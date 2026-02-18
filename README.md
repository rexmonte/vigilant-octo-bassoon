# OpenClaw Mac Mini Native Setup (No Pi)

This repository is for a **single-machine** OpenClaw deployment on a Mac Mini M4.
Everything runs natively on this Mac Mini. No Raspberry Pi involvement.

## Prerequisites
- macOS
- Git
- Homebrew
- Ollama
- Python 3.9+

## Setup

1. Clone repository

```bash
git clone https://github.com/rexmonte/vigilant-octo-bassoon.git
cd vigilant-octo-bassoon
```

2. Create `.env`

```bash
cp .env.example .env
nano .env
```

Use these variables:
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `OLLAMA_BASE_URL` (`http://127.0.0.1:11434`)
- `DISCORD_BOT_TOKEN`
- `DISCORD_ALERT_WEBHOOK`

3. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. Pull Ollama models

```bash
ollama pull qwen3:14b
ollama pull qwen2.5-coder:14b
```

5. Run preflight

```bash
python3 scripts/preflight.py
```

6. Resolve model targets

```bash
python3 scripts/resolve_model.py --role ace
python3 scripts/resolve_model.py --role worker
```

## Provider Tiers and Fallbacks

### Tier 1: Anthropic
- `claude-opus-4-6` (primary)
- `claude-sonnet-4` (fallback)
- `claude-haiku-4-5` (emergency)

### Tier 2: Google Gemini
- `gemini-2.5-pro`

### Tier 3: Ollama (local)
- `qwen3:14b`
- `qwen2.5-coder:14b`

### Open Fall chain
- ACE: Opus → Sonnet → Gemini → local (`qwen3:14b`)
- Worker: `qwen3:14b` → `qwen2.5-coder:14b` → Gemini → Haiku

If all tiers fail: send Discord alert, pause queue, and log to file.

## Troubleshooting (from your exact terminal output)

### `git pull origin main` says `Already up to date`
That means your local checkout already has the latest commit from `origin/main`.
To verify exactly what commit you're on:

```bash
git rev-parse --short HEAD
git log --oneline -n 3
```

If GitHub web UI still looks different, hard-refresh browser and confirm you are viewing the `main` branch.

### `/Users/clawdrex/.openclaw/completions/openclaw.zsh:...: command not found: compdef`
This usually means a Zsh completion file is being sourced in a shell context where Zsh completion isn't initialized.

Fix options:

1. Ensure you're using Zsh login shell:
```bash
echo $SHELL
```

2. In `~/.zshrc`, initialize completion before loading OpenClaw completions:
```bash
autoload -Uz compinit
compinit
```

3. Guard OpenClaw completion loading so it only runs when `compdef` exists:
```bash
command -v compdef >/dev/null && source ~/.openclaw/completions/openclaw.zsh
```

After edits:
```bash
source ~/.zshrc
```
