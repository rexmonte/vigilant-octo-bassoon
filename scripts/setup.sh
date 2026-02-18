#!/usr/bin/env bash
set -euo pipefail

echo "[1/7] Checking tools..."
command -v git >/dev/null || { echo "Git is required."; exit 1; }
command -v python3 >/dev/null || { echo "Python3 is required."; exit 1; }
command -v ollama >/dev/null || { echo "Ollama is required."; exit 1; }

echo "[2/7] Creating virtual environment (venv)..."
python3 -m venv venv
source venv/bin/activate

echo "[3/7] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[4/7] Preparing environment file..."
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from template. Fill required values before starting production."
else
  echo ".env already exists; keeping it unchanged."
fi

echo "[5/7] Verifying local Ollama..."
curl -fsS http://127.0.0.1:11434/api/tags >/dev/null || {
  echo "Ollama is not responding on 127.0.0.1:11434";
  exit 1;
}

echo "[6/7] Pulling required starter models..."
ollama pull qwen3:14b
ollama pull qwen2.5-coder:14b

echo "[7/7] Running preflight..."
python3 scripts/preflight.py || {
  echo "Preflight failed. Fix .env values and rerun.";
  exit 1;
}

echo "Setup complete. Start OpenClaw on this Mac Mini."
