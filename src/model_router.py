"""Role-aware model resolver for single-machine Mac Mini OpenClaw deployment."""

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
class ModelTarget:
    provider: str
    model: str
    role: str
    source: str


class ModelRouterError(RuntimeError):
    pass


def _setup_logging() -> logging.Logger:
    log_file = Path(os.getenv("LOG_FILE", "logs/model_router.log"))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("model_router")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def _load_config() -> Dict:
    if not CONFIG_PATH.exists():
        raise ModelRouterError(f"Missing config file: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _http_get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Tuple[int, Dict]:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        payload = json.loads(raw) if raw else {}
        return resp.status, payload


def _model_available(provider: str, model: str, cfg: Dict) -> bool:
    provider_cfg = cfg.get("providers", {}).get(provider)
    if not provider_cfg or not provider_cfg.get("enabled", False):
        return False
    return model in provider_cfg.get("models", [])


def _is_ollama_alive(cfg: Dict) -> bool:
    env_name = cfg.get("providers", {}).get("ollama", {}).get("base_url_env", "OLLAMA_BASE_URL")
    base_url = os.getenv(env_name, "http://127.0.0.1:11434")
    try:
        status, _ = _http_get_json(f"{base_url}/api/tags", timeout=6)
        return status == 200
    except Exception:
        return False


def _send_discord_alert(message: str) -> None:
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        return
    payload = json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass


def _chain_for_role(role: str, cfg: Dict) -> List[Tuple[str, str]]:
    role_cfg = cfg.get("roles", {}).get(role)
    if not role_cfg:
        raise ModelRouterError(f"Unknown role '{role}'.")
    chain = [
        (role_cfg["primary"]["provider"], role_cfg["primary"]["model"]),
        *[(item["provider"], item["model"]) for item in role_cfg.get("fallbacks", [])],
    ]
    return chain


def resolve_model(role: str = "ace", tried: Optional[List[Tuple[str, str]]] = None) -> ModelTarget:
    """Return best available model target for role with fallback traversal.

    If all models fail, this function logs a critical error and sends Discord alert.
    """
    cfg = _load_config()
    logger = _setup_logging()
    attempted = set(tried or [])

    for idx, (provider, model) in enumerate(_chain_for_role(role, cfg)):
        if (provider, model) in attempted:
            continue
        if not _model_available(provider, model, cfg):
            logger.warning("Model not enabled in config: %s/%s", provider, model)
            continue
        if provider == "ollama" and not _is_ollama_alive(cfg):
            logger.warning("Ollama unavailable while trying %s/%s", provider, model)
            continue
        source = "primary" if idx == 0 else f"fallback_{idx}"
        logger.info("Resolved role=%s provider=%s model=%s source=%s", role, provider, model, source)
        return ModelTarget(provider=provider, model=model, role=role, source=source)

    message = f"Open Fall triggered: all providers failed for role '{role}'. Queue should pause."
    logger.critical(message)
    _send_discord_alert(message)
    raise ModelRouterError("All provider tiers failed. Check logs/model_router.log and provider status.")
