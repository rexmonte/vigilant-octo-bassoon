"""Model/provider resolution with strict validation, aliases, and fallbacks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


CONFIG_PATH = Path("config/providers.json")


@dataclass(frozen=True)
class ResolvedModel:
    provider: str
    model: str
    from_fallback: bool = False


class ModelResolutionError(RuntimeError):
    """Raised when model selection cannot produce a valid provider/model pair."""


def load_config(path: Path = CONFIG_PATH) -> Dict:
    if not path.exists():
        raise ModelResolutionError(f"Config file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelResolutionError(f"Invalid JSON in {path}: {exc}") from exc


def _model_available(config: Dict, provider: str, model: str) -> bool:
    provider_cfg = config.get("providers", {}).get(provider)
    if not provider_cfg:
        return False
    if not provider_cfg.get("enabled", False):
        return False
    return model in provider_cfg.get("models", [])


def _fallback_candidates(config: Dict) -> List[Tuple[str, str]]:
    candidates = []
    for item in config.get("fallback_order", []):
        provider = item.get("provider")
        model = item.get("model")
        if provider and model:
            candidates.append((provider, model))
    return candidates


def _resolve_alias(
    config: Dict,
    provider: Optional[str],
    model: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve model alias from config.aliases.<name> = {provider, model}."""
    if provider or not model:
        return provider, model

    alias_cfg = config.get("aliases", {}).get(model)
    if not alias_cfg:
        return provider, model

    alias_provider = alias_cfg.get("provider")
    alias_model = alias_cfg.get("model")
    if alias_provider and alias_model:
        return alias_provider, alias_model
    return provider, model


def resolve_runtime_model(
    requested_provider: Optional[str] = None,
    requested_model: Optional[str] = None,
    config: Optional[Dict] = None,
) -> ResolvedModel:
    cfg = config or load_config()

    provider = requested_provider
    model = requested_model

    provider, model = _resolve_alias(cfg, provider, model)

    provider = provider or cfg.get("defaults", {}).get("provider")
    model = model or cfg.get("defaults", {}).get("model")

    if not provider or not model:
        raise ModelResolutionError("No requested model and no defaults configured.")

    if _model_available(cfg, provider, model):
        return ResolvedModel(provider=provider, model=model)

    for fallback_provider, fallback_model in _fallback_candidates(cfg):
        if _model_available(cfg, fallback_provider, fallback_model):
            return ResolvedModel(
                provider=fallback_provider,
                model=fallback_model,
                from_fallback=True,
            )

    raise ModelResolutionError(
        f"Requested model unavailable ({provider}/{model}) and no valid fallback found."
    )
