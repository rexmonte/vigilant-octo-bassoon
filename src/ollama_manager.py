"""Helpers for Ollama health checks and model pull operations."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Dict, List


def health_check(base_url: str, timeout: int = 10) -> Dict:
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            models = [m.get("name") for m in payload.get("models", [])]
            return {"ok": True, "message": "Ollama reachable", "models": models}
    except urllib.error.URLError as exc:
        return {"ok": False, "message": f"Ollama unreachable: {exc.reason}", "models": []}
    except TimeoutError:
        return {"ok": False, "message": "Ollama unreachable: timeout", "models": []}


def ensure_models(base_url: str, required_models: List[str], timeout: int = 10) -> Dict:
    status = health_check(base_url=base_url, timeout=timeout)
    if not status["ok"]:
        return {"ok": False, "message": status["message"], "missing_models": required_models}

    available = set(status.get("models", []))
    missing = [model for model in required_models if model not in available]
    if missing:
        return {
            "ok": False,
            "message": "Required Ollama models are missing. Pull them before startup.",
            "missing_models": missing,
        }
    return {"ok": True, "message": "All required Ollama models are available.", "missing_models": []}


def pull_model(base_url: str, model: str, timeout: int = 300, logger: logging.Logger | None = None) -> Dict:
    log = logger or logging.getLogger("ollama_manager")
    url = f"{base_url.rstrip('/')}/api/pull"
    payload = json.dumps({"name": model}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                return {"ok": False, "message": f"Failed to pull '{model}'. HTTP {response.status}"}
            log.info("Pulled model successfully: %s", model)
            return {"ok": True, "message": f"Pulled model successfully: {model}"}
    except urllib.error.URLError as exc:
        return {"ok": False, "message": f"Failed to pull '{model}': {exc.reason}"}
    except TimeoutError:
        return {"ok": False, "message": f"Failed to pull '{model}': timeout"}
