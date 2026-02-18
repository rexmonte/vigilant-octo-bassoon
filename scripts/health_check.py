#!/usr/bin/env python3
"""Operational health checks for local inference endpoints."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ollama_manager import health_check  # noqa: E402


def _load_local_env() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    _load_local_env()
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    timeout = int(os.getenv("INFERENCE_TIMEOUT", "30"))

    ollama = health_check(base_url=base_url, timeout=timeout)
    payload = {
        "ollama": ollama,
        "recommendation": "Do not expose OLLAMA port to the internet. Keep it local/LAN only.",
    }
    print(json.dumps(payload, indent=2))
    return 0 if ollama["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
