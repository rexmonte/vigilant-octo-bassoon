#!/usr/bin/env python3
"""CLI wrapper for model resolution checks and preflight validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.model_router import (
    ModelResolutionError,
    resolve_runtime_model,
    validate_environment,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a model from role policy and fallback chain."
    )
    parser.add_argument(
        "--role",
        choices=["ace", "worker"],
        default=None,
        help="Role to resolve using config roles.",
    )
    parser.add_argument("--provider", help="Requested provider name")
    parser.add_argument("--model", help="Requested model name")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run environment preflight checks.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.preflight:
        issues = validate_environment()
        if args.json:
            print(json.dumps({"ok": len(issues) == 0, "issues": issues}, indent=2))
        else:
            if issues:
                print("PREFLIGHT FAIL")
                for issue in issues:
                    print(f"- {issue}")
            else:
                print("PREFLIGHT OK")
        return 0 if len(issues) == 0 else 1

    if (args.provider and not args.model) or (args.model and not args.provider):
        print("If using explicit model selection, provide both --provider and --model.")
        return 2

    try:
        result = resolve_runtime_model(
            role=args.role,
            requested_provider=args.provider,
            requested_model=args.model,
        )
    except ModelResolutionError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}")
        return 1

    payload = {
        "ok": True,
        "provider": result.provider,
        "model": result.model,
        "source": "fallback" if result.from_fallback else "primary/requested",
        "role": result.role,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            "OK: "
            f"{result.provider}/{result.model} "
            f"(role={result.role}, source={payload['source']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
