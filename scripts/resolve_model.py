#!/usr/bin/env python3
"""CLI wrapper for model resolution checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.model_router import ModelResolutionError, resolve_runtime_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a provider/model against local catalog and fallback policy."
    )
    parser.add_argument("--provider", help="Requested provider name")
    parser.add_argument("--model", help="Requested model name")
    parser.add_argument(
        "--use-default",
        action="store_true",
        help="Resolve configured defaults instead of explicit provider/model",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.use_default and (not args.provider or not args.model):
        print("Either --use-default or both --provider and --model are required.")
        return 2

    try:
        result = resolve_runtime_model(
            requested_provider=None if args.use_default else args.provider,
            requested_model=None if args.use_default else args.model,
        )
    except ModelResolutionError as exc:
        print(f"ERROR: {exc}")
        return 1

    source = "fallback" if result.from_fallback else "requested/default"
    print(f"OK: {result.provider}/{result.model} (source={source})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
