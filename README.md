# OpenClaw / ACE Mac mini One-Shot Setup

This project is now focused on **getting you stable fast** on your new **Mac mini M4 (32GB RAM)** with minimal troubleshooting.

If your bot keeps dropping with errors like:

- `HTTP 404: model 'glm-4.7-flash' not found`

this setup gives you guardrails, fallback routing, and a practical architecture for multi-agents.

## Recommended architecture (simple + reliable)

- **ACE (head/orchestrator):** Anthropic API (`claude-3-7-sonnet-latest`)
- **Worker agents:** local models via Ollama (`qwen2.5:7b-instruct` default)
- **Fallback chain:** Anthropic Haiku ➜ local `llama3.1:8b`
- **Routing by task:** configured in `config/agent_stack.json`

This gives you strong reasoning at the top and low-cost local throughput for supporting agents.

## One-shot bootstrap

Run:

```bash
python3 scripts/bootstrap_mac_mini.py
```

This will:

1. Create `.env` from `.env.example` if missing.
2. Create `config/agent_stack.json` from template if missing.
3. Check core dependencies (`python3`, `git`, `ollama`).
4. Show your recommended runtime routing.

## Then do these 4 steps

1. Add your API keys in `.env`.
2. Start local runtime (`ollama serve`).
3. Pull a local model (`ollama pull qwen2.5:7b-instruct`).
4. Run the health check:

```bash
python3 scripts/healthcheck.py
```

## Key files

- `config/providers.json` — provider/model catalog, aliases, defaults, fallback order
- `config/agent_stack.example.json` — recommended multi-agent architecture for your hardware
- `src/model_router.py` — strict resolver used before each LLM API call
- `scripts/bootstrap_mac_mini.py` — one-shot machine bootstrap helper
- `scripts/healthcheck.py` — operational validation to avoid surprises

## Integration into your Discord bot

Before every LLM call:

1. Resolve provider/model via `resolve_runtime_model()`.
2. Call the matching API client.
3. If chosen model is unavailable, resolver auto-falls back.
4. Log provider/model used for observability.

Example:

```python
from src.model_router import resolve_runtime_model

choice = resolve_runtime_model(requested_model="ace-primary")
# use choice.provider and choice.model in your client
```

## Why this is better than hardcoding a model string

Hardcoded model names break migrations. This setup centralizes model policy, enables fallback, and gives you quick diagnostics before production calls.

For your specific failure (`glm-4.7-flash` 404), the resolver now shifts to healthy configured models instead of letting ACE crash.
