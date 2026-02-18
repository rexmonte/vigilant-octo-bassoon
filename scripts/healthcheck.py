#!/usr/bin/env python3
"""Operational health check for provider/model configuration."""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.model_router import ModelResolutionError, load_config, resolve_runtime_model


def check_env_keys() -> dict:
    return {
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "ZHIPU_API_KEY": bool(os.getenv("ZHIPU_API_KEY")),
    }


def check_local_endpoint(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def main() -> int:
    config = load_config()

    print("== Model resolution checks ==")
    try:
        default_result = resolve_runtime_model(config=config)
        print(f"- default: OK -> {default_result.provider}/{default_result.model}")
    except ModelResolutionError as exc:
        print(f"- default: ERROR -> {exc}")
        return 1

    aliases = config.get("aliases", {})
    for alias_name in aliases:
        try:
            result = resolve_runtime_model(requested_model=alias_name, config=config)
            source = "fallback" if result.from_fallback else "direct"
            print(f"- alias '{alias_name}': OK -> {result.provider}/{result.model} ({source})")
        except ModelResolutionError as exc:
            print(f"- alias '{alias_name}': ERROR -> {exc}")
            return 1

    print("\n== Environment checks ==")
    env_status = check_env_keys()
    for name, present in env_status.items():
        print(f"- {name}: {'set' if present else 'missing'}")

    local_url = os.getenv("LOCAL_OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
    local_ok = check_local_endpoint(local_url)
    print(f"- LOCAL_OPENAI_BASE_URL reachable ({local_url}): {'yes' if local_ok else 'no'}")

    print("\nHealth check complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
