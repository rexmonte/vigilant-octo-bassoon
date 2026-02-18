#!/usr/bin/env python3
"""CLI for preflight validation and role-based model resolution."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.model_router import (  # noqa: E402
    ModelResolutionError,
    configure_logging,
    resolve_runtime_model,
    validate_environment,
)


def _load_local_env() -> None:
    """Best-effort .env loader without extra dependencies."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenClaw model routing utility")
    parser.add_argument("--role", choices=["ace", "worker"], help="Role to resolve", default=None)
    parser.add_argument("--provider", help="Optional explicit provider")
    parser.add_argument("--model", help="Optional explicit model")
    parser.add_argument("--preflight", action="store_true", help="Run startup preflight checks")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    return parser.parse_args()


def main() -> int:
    _load_local_env()
    configure_logging()
    log = logging.getLogger("resolve_model")
    args = parse_args()

    if args.preflight:
        failures = validate_environment()
        payload = {"ok": len(failures) == 0, "failures": failures}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            if payload["ok"]:
                print("PREFLIGHT OK: startup checks passed.")
            else:
                print("PREFLIGHT FAILED:")
                for failure in failures:
                    print(f"- {failure}")
        return 0 if payload["ok"] else 1

    if (args.provider and not args.model) or (args.model and not args.provider):
        print("ERROR: Provide both --provider and --model when using explicit selection.")
        return 2

    try:
        resolved = resolve_runtime_model(
            role=args.role,
            requested_provider=args.provider,
            requested_model=args.model,
        )
    except ModelResolutionError as exc:
        log.error("Resolution failed: %s", exc)
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}")
        return 1

    output = {
        "ok": True,
        "role": resolved.role,
        "provider": resolved.provider,
        "model": resolved.model,
        "source": resolved.source,
        "retry_count": int(os.getenv("FALLBACK_RETRY_COUNT", "3")),
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(
            "RESOLVED: "
            f"role={output['role']} provider={output['provider']} "
            f"model={output['model']} source={output['source']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
