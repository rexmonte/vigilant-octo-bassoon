# Discord Agent Migration Helper (Pi ➜ Mac mini)

This repository contains a minimal, provider-agnostic model router to prevent runtime failures like:

- `HTTP 404: model 'glm-4.7-flash' not found`

It is designed to help you migrate an existing Discord/ACE-style agent stack from a failed Raspberry Pi to a Mac mini and keep your bot online even when a configured model is invalid.

## What this solves

- Validates provider/model combinations **before** your bot sends requests.
- Adds a safe fallback chain (Anthropic first, local model second by default).
- Lets you keep one logical model alias in your bot code while changing real providers/models in config.

## Quick start

1. Copy the environment template:

```bash
cp .env.example .env
```

2. (Optional) edit provider defaults in `config/providers.json`.

3. Resolve a model your bot wants to use:

```bash
python3 scripts/resolve_model.py --provider zhipu --model glm-4.7-flash
```

If unavailable, the script exits non-zero and prints the configured fallback.

4. Ask for the configured default runtime model:

```bash
python3 scripts/resolve_model.py --use-default
```

## Integration pattern for your Discord bot

Before making an LLM API call:

1. Load `.env`.
2. Call `resolve_runtime_model()` from `src/model_router.py`.
3. Use the returned provider/model in your API client.
4. If resolution fails, surface an alert and/or switch to your local backup model.

## Suggested migration defaults

- Primary: `anthropic/claude-3-7-sonnet-latest` (or newer Anthropic model you have access to)
- Secondary fallback: local OpenAI-compatible endpoint (e.g., Ollama)
- Only keep `glm-*` models enabled if your account and endpoint support them.

## Files

- `src/model_router.py` — provider/model validation and fallback resolution
- `scripts/resolve_model.py` — CLI smoke test helper for operations
- `config/providers.json` — editable model catalog + fallback policy
- `.env.example` — environment variables for your bot runtime
