"""Production model router for Anthropic -> Gemini -> Ollama fallback routing."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CONFIG_PATH = Path("config/providers.json")


@dataclass(frozen=True)
class ResolvedModel:
    provider: str
    model: str
    role: str
    source: str


class ModelResolutionError(RuntimeError):
    pass


class PreflightError(RuntimeError):
    pass


def configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "info").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def load_config(path: Path = CONFIG_PATH) -> Dict:
    if not path.exists():
        raise ModelResolutionError(f"Config file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelResolutionError(f"Invalid JSON in {path}: {exc}") from exc


def _provider_cfg(config: Dict, provider: str) -> Optional[Dict]:
    return config.get("providers", {}).get(provider)


def _is_model_enabled(config: Dict, provider: str, model: str) -> bool:
    provider_cfg = _provider_cfg(config, provider)
    if not provider_cfg or not provider_cfg.get("enabled", False):
        return False
    return model in provider_cfg.get("models", [])


def _check_ollama_connectivity(base_url: str, timeout: int) -> Optional[str]:
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return f"Ollama returned HTTP {response.status}"
    except urllib.error.URLError as exc:
        return f"Cannot connect to Ollama at {base_url}: {exc.reason}"
    except TimeoutError:
        return f"Cannot connect to Ollama at {base_url}: connection timed out"
    return None


def _candidate_chain(config: Dict, role: str) -> List[Tuple[str, str]]:
    role_cfg = config.get("roles", {}).get(role)
    if not role_cfg:
        raise ModelResolutionError(f"Unknown role '{role}'. Check config/providers.json roles.")

    chain: List[Tuple[str, str]] = []
    primary = role_cfg.get("primary", {})
    if not primary.get("provider") or not primary.get("model"):
        raise ModelResolutionError(f"Role '{role}' missing primary provider/model.")

    chain.append((primary["provider"], primary["model"]))

    for fallback in role_cfg.get("fallbacks", []):
        provider = fallback.get("provider")
        model = fallback.get("model")
        if provider and model:
            chain.append((provider, model))

    return chain


def validate_environment(config: Optional[Dict] = None) -> List[str]:
    cfg = config or load_config()
    failures: List[str] = []

    required_envs = [
        "ANTHROPIC_TOKEN",
        "GOOGLE_API_KEY",
        "OLLAMA_BASE_URL",
        "DISCORD_BOT_TOKEN",
        "DISCORD_GUILD_ID",
        "INFERENCE_TIMEOUT",
        "FALLBACK_RETRY_COUNT",
    ]

    for env_name in required_envs:
        if not os.getenv(env_name):
            failures.append(f"Missing required environment variable: {env_name}")

    providers = cfg.get("providers", {})
    timeout = int(os.getenv("INFERENCE_TIMEOUT", "10"))
    for provider_name, provider_cfg in providers.items():
        if not provider_cfg.get("enabled", False):
            continue

        for auth_env in provider_cfg.get("auth_env", []):
            if not os.getenv(auth_env):
                failures.append(
                    f"Provider '{provider_name}' requires env '{auth_env}', but it is missing."
                )

        base_url_env = provider_cfg.get("base_url_env")
        if base_url_env:
            base_url = os.getenv(base_url_env)
            if not base_url:
                failures.append(
                    f"Provider '{provider_name}' requires env '{base_url_env}', but it is missing."
                )
            elif provider_name == "ollama":
                err = _check_ollama_connectivity(base_url=base_url, timeout=timeout)
                if err:
                    failures.append(err)

    for role_name in cfg.get("roles", {}):
        try:
            _candidate_chain(cfg, role_name)
        except ModelResolutionError as exc:
            failures.append(str(exc))

    return failures


def resolve_runtime_model(
    role: Optional[str] = None,
    requested_provider: Optional[str] = None,
    requested_model: Optional[str] = None,
    config: Optional[Dict] = None,
    logger: Optional[logging.Logger] = None,
) -> ResolvedModel:
    cfg = config or load_config()
    log = logger or logging.getLogger("model_router")
    selected_role = role or cfg.get("defaults", {}).get("role", "ace")

    if requested_provider and requested_model:
        if _is_model_enabled(cfg, requested_provider, requested_model):
            log.info(
                "Resolved model | role=%s provider=%s model=%s source=explicit",
                selected_role,
                requested_provider,
                requested_model,
            )
            return ResolvedModel(requested_provider, requested_model, selected_role, "explicit")

        log.warning(
            "Explicit model unavailable | role=%s provider=%s model=%s. Falling back.",
            selected_role,
            requested_provider,
            requested_model,
        )

    for idx, (provider, model) in enumerate(_candidate_chain(cfg, selected_role)):
        source = "primary" if idx == 0 else f"fallback_{idx}"
        if _is_model_enabled(cfg, provider, model):
            log.info(
                "Resolved model | role=%s provider=%s model=%s source=%s",
                selected_role,
                provider,
                model,
                source,
            )
            return ResolvedModel(provider, model, selected_role, source)

    raise ModelResolutionError(
        f"No available model for role '{selected_role}'. Check provider enablement and model IDs."
    )


def resolve_with_retry(
    role: str,
    error_reason: str,
    tried: Optional[List[Tuple[str, str]]] = None,
    config: Optional[Dict] = None,
    logger: Optional[logging.Logger] = None,
) -> ResolvedModel:
    cfg = config or load_config()
    log = logger or logging.getLogger("model_router")
    tried_set = set(tried or [])

    for provider, model in _candidate_chain(cfg, role):
        if (provider, model) in tried_set:
            continue
        if _is_model_enabled(cfg, provider, model):
            log.warning(
                "Retrying with fallback | role=%s provider=%s model=%s reason=%s",
                role,
                provider,
                model,
                error_reason,
            )
            return ResolvedModel(provider, model, role, "retry_fallback")

    raise ModelResolutionError(
        f"All fallback models exhausted for role '{role}'. Last error: {error_reason}"
    )


def run_preflight_or_raise(config: Optional[Dict] = None) -> None:
    failures = validate_environment(config=config)
    if failures:
        message = "Preflight failed:\n- " + "\n- ".join(failures)
        raise PreflightError(message)
