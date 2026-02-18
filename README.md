# Vigilant Octo Bassoon — OpenClaw Mac Mini Runtime

Production-ready, single-machine OpenClaw runtime for a **Mac Mini M4 (32GB RAM)**.

## Architecture (single machine)

- **ACE (orchestrator, user-facing):** cloud-first intelligence
- **Worker agents (subordinate):** local-first execution
- **Three-tier inference hierarchy:**
  1. Anthropic (cloud)
  2. Google Gemini (cloud)
  3. Ollama (local)

> Security rule: keep Ollama local/LAN only. **Never expose port 11434 to the internet.**

## Model policy

### ACE fallback chain
1. `anthropic/claude-opus-4-6`
2. `anthropic/claude-sonnet-4`
3. `google/gemini-2.5-pro`
4. `ollama/qwen3:14b`

### Worker fallback chain
1. `ollama/qwen3:14b`
2. `ollama/qwen2.5-coder:14b`
3. `google/gemini-2.5-pro`
4. `anthropic/claude-haiku-4-5`

## Local model optimization (M4, 32GB unified memory)

Use **Q4_K_M** quantized builds for best speed/quality balance.

- `qwen3:14b` → ~10GB peak, ~40-50 tok/s
- `qwen2.5-coder:14b` → ~10GB peak, ~40-50 tok/s
- `qwen3-30b-a3b` → ~18-20GB peak, ~25-35 tok/s (heavy reasoning only)
- `gemma3-27b` → ~16GB peak, ~30-40 tok/s

Keep at least **4-5GB free** for macOS + OpenClaw processes.

Future optimization option: on macOS M4, MLX backends (e.g., LM Studio + MLX) often deliver a **15-40% speed boost** vs default Ollama path.

---

## 10-minute setup (fresh machine)

### 1) Verify Git
```bash
git --version
```

### 2) Clone
```bash
git clone https://github.com/rexmonte/vigilant-octo-bassoon.git
cd vigilant-octo-bassoon
```

### 3) Create `.env`
```bash
cp .env.example .env
nano .env
```

Environment meanings:
- `ANTHROPIC_TOKEN`: session token for Anthropic access
- `GOOGLE_API_KEY`: Gemini API key
- `OLLAMA_BASE_URL`: local Ollama API endpoint
- `OLLAMA_HOST`: Ollama bind host
- `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`: Discord interface configuration
- `LOG_LEVEL`: runtime logging verbosity
- `INFERENCE_TIMEOUT`: per-request timeout seconds
- `FALLBACK_RETRY_COUNT`: maximum fallback retries

### 4) Verify Ollama
```bash
curl http://localhost:11434/api/tags
```

### 5) Pull required models
```bash
ollama pull qwen3:14b
ollama pull qwen2.5-coder:14b
```

### 6) Install Python deps
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 7) Run preflight
```bash
python3 scripts/resolve_model.py --preflight
```

### 8) Resolve ACE role
```bash
python3 scripts/resolve_model.py --role ace
```

### 9) Start OpenClaw
```bash
openclaw start
```

### 10) Smoke test
- Send a test task through Discord to ACE, or
- Run local health command:
```bash
python3 scripts/health_check.py
```

---

## Repository layout

```text
vigilant-octo-bassoon/
├── config/
│   ├── providers.json
│   └── agents.json
├── src/
│   ├── model_router.py
│   ├── ollama_manager.py
│   └── discord_interface.py
├── scripts/
│   ├── resolve_model.py
│   ├── setup.sh
│   └── health_check.py
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Optional Docker path

Native Ollama is preferred on M4. If you want container consistency:

```bash
docker compose up -d
```
