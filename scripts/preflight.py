#!/usr/bin/env python3
"""Preflight checks for single-machine Mac Mini OpenClaw deployment."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple


def _load_env() -> None:
    env_file = Path('.env')
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        os.environ.setdefault(key.strip(), val.strip())


def _get(url: str, headers: Dict[str, str] | None = None, timeout: int = 10) -> Tuple[bool, str, Dict]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode('utf-8') or '{}')
            return True, f"HTTP {resp.status}", payload
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}", {}
    except Exception as exc:
        return False, str(exc), {}


def check_anthropic() -> Tuple[bool, str]:
    token = os.getenv('ANTHROPIC_API_KEY', '').strip()
    if not token:
        return False, 'Missing ANTHROPIC_API_KEY'
    ok, msg, _ = _get(
        'https://api.anthropic.com/v1/models',
        headers={
            'x-api-key': token,
            'anthropic-version': '2023-06-01'
        },
        timeout=12,
    )
    if ok:
        return True, 'Anthropic API key accepted by /v1/models'
    return False, f'Anthropic check failed ({msg}). Check key and account access.'


def check_google() -> Tuple[bool, str]:
    key = os.getenv('GOOGLE_API_KEY', '').strip()
    if not key:
        return False, 'Missing GOOGLE_API_KEY'
    ok, msg, _ = _get(
        f'https://generativelanguage.googleapis.com/v1beta/models?key={key}',
        timeout=12,
    )
    if ok:
        return True, 'Google API key accepted by models endpoint'
    return False, f'Google check failed ({msg})'


def check_ollama() -> Tuple[bool, str]:
    base = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
    ok, msg, payload = _get(f'{base}/api/tags', timeout=6)
    if not ok:
        return False, f'Ollama unreachable at {base} ({msg})'
    models = payload.get('models', [])
    if not models:
        return False, 'Ollama reachable, but no models are pulled yet'
    return True, f"Ollama reachable with {len(models)} model(s)"


def check_discord_bot() -> Tuple[bool, str]:
    token = os.getenv('DISCORD_BOT_TOKEN', '').strip()
    if not token:
        return False, 'Missing DISCORD_BOT_TOKEN'
    ok, msg, payload = _get(
        'https://discord.com/api/v10/users/@me',
        headers={'Authorization': f'Bot {token}'},
        timeout=10,
    )
    if ok:
        user = payload.get('username', 'unknown')
        return True, f'Discord bot token valid for @{user}'
    return False, f'Discord bot check failed ({msg})'


def main() -> int:
    _load_env()
    checks: List[Tuple[str, Tuple[bool, str]]] = [
        ('Anthropic', check_anthropic()),
        ('Google Gemini', check_google()),
        ('Ollama', check_ollama()),
        ('Discord Bot', check_discord_bot()),
    ]

    has_fail = False
    print('OpenClaw Mac Mini Preflight Results')
    print('----------------------------------')
    for name, (ok, message) in checks:
        status = 'OK' if ok else 'FAIL'
        print(f'[{status}] {name}: {message}')
        if not ok:
            has_fail = True

    if has_fail:
        print('\nPreflight failed. Fix the failed checks above before starting OpenClaw.')
        return 1

    print('\nPreflight passed. System is ready for startup.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
