# ACE Migration Runtime (Pi ➜ M4 Mac mini)

This project now provides a production-oriented **model routing + fallback policy** for your migration with explicit support for:

- ACE primary on `claude-opus-4.6`
- ACE optional swap to `claude-sonnet-4.6`
- Worker-first local models via Ollama
- Open Fall protocol: **degrade → log → notify**

## Why this fixes your current instability

The repeated Discord error (`HTTP 404: model 'glm-4.7-flash' not found`) usually means a model ID/provider mismatch. This runtime prevents bad model IDs from being used at runtime by resolving through a strict catalog and role-specific fallback chains.

## Architecture (recommended)

- **ACE role**
  - Primary: `anthropic/claude-opus-4.6`
  - Fallback 1: `anthropic/claude-sonnet-4.6`
  - Fallback 2: `anthropic/claude-haiku-4.5`
  - Fallback 3: `ollama/llama-4-8b-instruct`
- **Worker role**
  - Primary: `ollama/llama-4-8b-instruct`
  - Fallback 1: `ollama/mistral-small`
  - Fallback 2: `anthropic/claude-haiku-4.5`

All role routing is defined in `config/providers.json`.

## Quick start

1. Copy environment template:

```bash
cp .env.example .env
```

2. Fill at least:

- `ANTHROPIC_API_KEY`
- `LOCAL_OPENAI_BASE_URL` (default points to local Ollama)

3. Run preflight:

```bash
python3 scripts/resolve_model.py --preflight
```

4. Resolve ACE role:

```bash
python3 scripts/resolve_model.py --role ace
```

5. Resolve worker role:

```bash
python3 scripts/resolve_model.py --role worker
```

## Docker runtime for local fallback

Start local services:

```bash
docker compose up -d
```

Then pull a model into Ollama (example):

```bash
docker exec -it ace-ollama ollama pull llama-4-8b-instruct
```

## Integration point in your bot

Before every LLM call:

1. Resolve role model via `resolve_runtime_model(role="ace")` or `resolve_runtime_model(role="worker")`.
2. Call the chosen provider/model.
3. On upstream failure, re-resolve and route to fallback.
4. If all fail, execute Open Fall protocol (degrade queue, log, Discord webhook alert).

## Files

- `src/model_router.py`: role-aware resolver + environment preflight
- `scripts/resolve_model.py`: CLI for resolution/preflight
- `config/providers.json`: provider catalog + role routing + Open Fall settings
- `docker-compose.yml`: Ollama + Qdrant baseline stack for macOS
- `.env.example`: minimal env template
