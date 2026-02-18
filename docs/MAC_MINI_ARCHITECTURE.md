# Mac mini M4 (32GB) multi-agent architecture blueprint

## Goal
A persistent, low-maintenance system where ACE orchestrates and delegates to specialized workers.

## Recommended topology

1. **ACE Orchestrator (cloud, high quality)**
   - Provider: Anthropic
   - Model: `claude-3-7-sonnet-latest`
   - Responsibilities: planning, task decomposition, safety checks, final synthesis.

2. **Worker Lane A (local, coding / tool use)**
   - Provider: local OpenAI-compatible endpoint (Ollama)
   - Model: `qwen2.5:7b-instruct`

3. **Worker Lane B (local, resilient fallback)**
   - Provider: local OpenAI-compatible endpoint
   - Model: `llama3.1:8b`

4. **Emergency fallback (cloud cheap)**
   - Provider: Anthropic
   - Model: `claude-3-5-haiku-latest`

## Runtime policy

- Keep ACE cloud-first for quality.
- Run repetitive or high-volume workers locally.
- Always resolve model/provider through `src/model_router.py`.
- Keep one alias per role (`ace-primary`, `worker-local`, etc.) so swaps are config-only.

## Operational hardening checklist

- Use separate API keys for prod vs experiments.
- Add request timeout and max retries per lane.
- Enable simple circuit breaker per provider.
- Log: timestamp, agent-role, provider/model, latency, error class.
- Run `scripts/healthcheck.py` before restarting production services.

## Capacity notes for your hardware

- 32GB RAM can comfortably run one 7B model with headroom for app workloads.
- For concurrent heavy local workloads, queue requests and cap parallelism.
- Prefer fewer stable models over many partially-tested ones.
