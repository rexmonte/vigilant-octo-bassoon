"""Model/provider resolution with role-aware fallbacks and preflight checks."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


CONFIG_PATH = Path("config/providers.json")


@dataclass(frozen=True)
class ResolvedModel:
    provider: str
    model: str
    from_fallback: bool = False
    role: Optional[str] = None


class ModelResolutionError(RuntimeError):
    pass


def load_config(path: Path = CONFIG_PATH) -> Dict:
    if not path.exists():
        raise ModelResolutionError(f"Config file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelResolutionError(f"Invalid JSON in {path}: {exc}") from exc


def _provider_cfg(config: Dict, provider: str) -> Optional[Dict]:
    return config.get("providers", {}).get(provider)


def _model_available(config: Dict, provider: str, model: str) -> bool:
    provider_cfg = _provider_cfg(config, provider)
    if not provider_cfg:
        return False
    if not provider_cfg.get("enabled", False):
        return False
    return model in provider_cfg.get("models", [])


def _role_plan(config: Dict, role: str) -> Tuple[Tuple[str, str], List[Tuple[str, str]]]:
    role_cfg = config.get("roles", {}).get(role)
    if not role_cfg:
        raise ModelResolutionError(f"Unknown role: {role}")

    primary = role_cfg.get("primary", {})
    provider = primary.get("provider")
    model = primary.get("model")
    if not provider or not model:
        raise ModelResolutionError(f"Role '{role}' is missing a valid primary model.")

    fallbacks: List[Tuple[str, str]] = []
    for item in role_cfg.get("fallbacks", []):
        fallback_provider = item.get("provider")
        fallback_model = item.get("model")
        if fallback_provider and fallback_model:
            fallbacks.append((fallback_provider, fallback_model))

    return (provider, model), fallbacks


def _iter_candidates(
    config: Dict,
    role: Optional[str],
    requested_provider: Optional[str],
    requested_model: Optional[str],
) -> Tuple[Tuple[str, str], List[Tuple[str, str]]]:
    if requested_provider and requested_model:
        role_name = role or config.get("defaults", {}).get("role", "ace")
        _, role_fallbacks = _role_plan(config, role_name)
        return (requested_provider, requested_model), role_fallbacks

    role_name = role or config.get("defaults", {}).get("role")
    if not role_name:
        raise ModelResolutionError("No role selected and no defaults.role configured.")

    return _role_plan(config, role_name)


def resolve_runtime_model(
    role: Optional[str] = None,
    requested_provider: Optional[str] = None,
    requested_model: Optional[str] = None,
    config: Optional[Dict] = None,
) -> ResolvedModel:
    cfg = config or load_config()

    primary, fallbacks = _iter_candidates(cfg, role, requested_provider, requested_model)
    provider, model = primary

    effective_role = role or cfg.get("defaults", {}).get("role")

    if _model_available(cfg, provider, model):
        return ResolvedModel(provider=provider, model=model, role=effective_role)

    for fallback_provider, fallback_model in fallbacks:
        if _model_available(cfg, fallback_provider, fallback_model):
            return ResolvedModel(
                provider=fallback_provider,
                model=fallback_model,
                from_fallback=True,
                role=effective_role,
            )

    raise ModelResolutionError(
        f"Requested model unavailable ({provider}/{model}) and no valid fallback found."
    )


def validate_environment(config: Optional[Dict] = None) -> List[str]:
    """Return a list of preflight issues; empty list means healthy enough to boot."""
    cfg = config or load_config()
    issues: List[str] = []

    providers = cfg.get("providers", {})
    for provider_name, provider_cfg in providers.items():
        if not provider_cfg.get("enabled", False):
            continue

        key_env = provider_cfg.get("requires_key_env")
        if key_env and not os.getenv(key_env):
            issues.append(
                f"Provider '{provider_name}' enabled but missing env '{key_env}'."
            )

        base_url_env = provider_cfg.get("base_url_env")
        if base_url_env and not os.getenv(base_url_env):
            issues.append(
                f"Provider '{provider_name}' enabled but missing env '{base_url_env}'."
            )

    for role_name in cfg.get("roles", {}):
        try:
            resolve_runtime_model(role=role_name, config=cfg)
        except ModelResolutionError as exc:
            issues.append(f"Role '{role_name}' failed resolution: {exc}")

    return issues
