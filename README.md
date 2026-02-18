# OpenClaw Mac Mini Native Setup (No Pi)

This repository is a clean, single-machine OpenClaw runtime for Scott's **Mac Mini M4 (32GB RAM)**.
Everything runs on this one Mac Mini. No Raspberry Pi involvement.

## Prerequisites

- macOS on Mac Mini M4
- Git
- Homebrew
- Ollama
- Python 3.9+

Quick checks:

```bash
git --version
python3 --version
brew --version
ollama --version
```

## 1) Clone repository

```bash
git clone https://github.com/rexmonte/vigilant-octo-bassoon.git
cd vigilant-octo-bassoon
```

## 2) Create `.env` with secrets

```bash
cp .env.example .env
nano .env
```

Required values:

- `ANTHROPIC_SESSION_TOKEN` — Anthropic session token method
- `GOOGLE_API_KEY` — Gemini 2.5 Pro API key
- `OLLAMA_BASE_URL` — local endpoint (`http://127.0.0.1:11434`)
- `DISCORD_BOT_TOKEN` — ACE Discord bot token
- `DISCORD_WEBHOOK_URL` — used for Open Fall alerts when all providers fail

## 3) Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4) Pull local worker models

```bash
ollama pull qwen3:14b
ollama pull qwen2.5-coder:14b
```

Optional local fallbacks:

```bash
ollama pull mistral-7b
ollama pull llama2:13b
```

Upgrade path (smarter but heavier):

```bash
ollama pull qwen3-30b-a3b
ollama pull gemma3-27b
```

## 5) Run preflight checks

```bash
python3 scripts/preflight.py
```

Preflight verifies:

- Anthropic token presence + remote check
- Google API key presence + remote check
- Ollama connectivity + at least one model pulled
- Discord bot token validity

## 6) Resolve model targets

ACE model resolution:

```bash
python3 scripts/resolve_model.py --role ace
```

Worker model resolution:

```bash
python3 scripts/resolve_model.py --role worker
```

## 7) Integrate with OpenClaw on this Mac Mini

Use `src/model_router.py` in your OpenClaw agent runtime:

- `resolve_model(role="ace")` for ACE orchestrator
- `resolve_model(role="worker")` for worker tasks

If a model/provider fails, call `resolve_model(..., tried=[...])` pattern in your runtime loop and retry next fallback.

## Tiered provider architecture

1. **Tier 1 (Anthropic)**
   - `claude-opus-4-6` (primary)
   - `claude-sonnet-4` (fallback)
   - `claude-haiku-4-5` (emergency)
2. **Tier 2 (Google Gemini)**
   - `gemini-2.5-pro` (sub-boss / credit-backed fallback)
3. **Tier 3 (Ollama local)**
   - `qwen3:14b` (primary worker)
   - `qwen2.5-coder:14b` (coding)
   - `mistral-7b` / `llama2:13b` (extra fallback)
   - Upgrade path: `qwen3-30b-a3b`, `gemma3-27b`

### Open Fall protocol

When all provider tiers fail:

1. Send Discord webhook alert
2. Pause queue
3. Log details to file (`logs/model_router.log`)

## Local safety note

Keep Ollama local-only on this machine (`127.0.0.1`) unless you intentionally expose it to a trusted LAN.
Never expose Ollama to the public internet.
