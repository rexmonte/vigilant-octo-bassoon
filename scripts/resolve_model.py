#!/usr/bin/env python3
"""Resolve role model target using configured fallback chain."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.model_router import ModelRouterError, resolve_model  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Resolve model target for OpenClaw role')
    parser.add_argument('--role', choices=['ace', 'worker'], default='ace')
    parser.add_argument('--json', action='store_true')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        target = resolve_model(role=args.role)
    except ModelRouterError as exc:
        if args.json:
            print(json.dumps({'ok': False, 'error': str(exc)}, indent=2))
        else:
            print(f'ERROR: {exc}')
        return 1

    payload = {
        'ok': True,
        'role': target.role,
        'provider': target.provider,
        'model': target.model,
        'source': target.source,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"RESOLVED role={target.role} provider={target.provider} "
            f"model={target.model} source={target.source}"
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
