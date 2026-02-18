#!/usr/bin/env python3
"""One-shot bootstrap for Mac mini multi-agent setup."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
STACK_EXAMPLE = ROOT / "config" / "agent_stack.example.json"
STACK_PATH = ROOT / "config" / "agent_stack.json"


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def write_env_if_missing() -> bool:
    if ENV_PATH.exists():
        return False
    ENV_PATH.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return True


def write_stack_if_missing() -> bool:
    if STACK_PATH.exists():
        return False
    STACK_PATH.write_text(STACK_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return True


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def health_snapshot() -> dict:
    checks = {
        "python3": command_exists("python3"),
        "ollama": command_exists("ollama"),
        "git": command_exists("git"),
    }

    ollama_running = False
    if checks["ollama"]:
        try:
            run = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            ollama_running = run.returncode == 0
        except Exception:
            ollama_running = False

    checks["ollama_reachable"] = ollama_running
    return checks


def main() -> int:
    env_created = write_env_if_missing()
    stack_created = write_stack_if_missing()

    providers = read_json(ROOT / "config" / "providers.json")
    stack = read_json(STACK_PATH if STACK_PATH.exists() else STACK_EXAMPLE)

    print("== Mac mini bootstrap summary ==")
    print(f"Created .env: {'yes' if env_created else 'no (already existed)'}")
    print(
        f"Created config/agent_stack.json: {'yes' if stack_created else 'no (already existed)'}"
    )

    health = health_snapshot()
    print("\n== Local dependency checks ==")
    for name, ok in health.items():
        print(f"- {name}: {'OK' if ok else 'MISSING/NOT RUNNING'}")

    print("\n== Recommended routing ==")
    print(
        f"ACE orchestrator: {stack['ace_orchestrator']['provider']}/{stack['ace_orchestrator']['model']}"
    )
    print(
        f"Worker default: {stack['worker_defaults']['provider']}/{stack['worker_defaults']['model']}"
    )

    if not health["ollama"]:
        print("\nInstall local model runtime: brew install ollama")
    elif not health["ollama_reachable"]:
        print("\nStart local model runtime: ollama serve")

    default = providers["defaults"]
    print(
        "\nProvider default in catalog: "
        f"{default['provider']}/{default['model']}"
    )
    print("\nNext steps:")
    print("1) Fill API keys in .env")
    print("2) Pull local model: ollama pull qwen2.5:7b-instruct")
    print("3) Validate routing: python3 scripts/healthcheck.py")
    print("4) Start your Discord bot with resolved provider/model from src/model_router.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
