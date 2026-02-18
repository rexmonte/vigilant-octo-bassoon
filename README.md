# ACE Migration Runtime (Pi ➜ M4 Mac mini)

This project provides a **role-based model router + preflight checks** tuned to your architecture:

- ACE on Anthropic first
- Gemini as cloud sub-fallback
- Local Mac Mini models for worker-heavy and degraded operation
- Open Fall protocol: **degrade → log → notify → hold queue**

## Locked-in model routing (from your environment)

### ACE role
1. `anthropic/claude-opus-4-6` (primary)
2. `anthropic/claude-sonnet-4`
3. `google/gemini-2.5-pro`
4. `ollama/qwen3-30b-a3b`
5. `anthropic/claude-haiku-4-5` (emergency)

### Worker role
1. `ollama/qwen3-30b-a3b` (primary)
2. `ollama/gemma3-27b`
3. `ollama/mistral-small`
4. `anthropic/claude-haiku-4-5`

All routing policy is in `config/providers.json`.

## OpenClaw alignment notes

- Active ACE path should be `~/.openclaw/agents/ace/` (not `agents/main/`).
- Key config files:
  - `~/.openclaw/agents/ace/agent/models.json`
  - `~/.openclaw/agents/ace/agent/auth-profiles.json`
- Anthropic provider API style should remain `anthropic-messages` in OpenClaw-side config.

## Quick start

1. Copy env template:

```bash
cp .env.example .env
```

2. Fill required values:

- `ANTHROPIC_API_KEY` **or** `ANTHROPIC_AUTH_TOKEN`
- `GOOGLE_API_KEY` (if Gemini fallback enabled)
- `LOCAL_OPENAI_BASE_URL` (`http://192.168.0.100:11434/v1` from Pi)
- `DISCORD_ALERT_WEBHOOK`

3. Run preflight:

```bash
python3 scripts/resolve_model.py --preflight
```

4. Resolve role targets:

```bash
python3 scripts/resolve_model.py --role ace
python3 scripts/resolve_model.py --role worker
```

5. Validate bad model fallback behavior:

```bash
python3 scripts/resolve_model.py --provider zhipu --model glm-4.7-flash
```

## Docker (optional baseline)

If you want containerized local services:

```bash
docker compose up -d
```

For native Mac mini launchd Ollama, keep `LOCAL_OPENAI_BASE_URL` pointed at the Mac host.

## Integration point in your bot

Before every LLM call:

1. Resolve role model via `resolve_runtime_model(role="ace")` or `resolve_runtime_model(role="worker")`.
2. Call provider/model.
3. If call fails, re-resolve and retry on fallback.
4. If all providers fail, trigger Open Fall: queue hold + Discord alert + triage mode.
