---
title: AIDE v5
emoji: "🧪"
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# AIDE v5

AIDE (Alloy Intelligence and Design Engine) provides alloy analysis and design with multi-domain physics scoring, contextual weighting, and conversational workflows.

## What It Does

- Evaluates alloys across 42 physics and engineering domains.
- Computes weighted and raw composite scores with pass/warn/fail checks.
- Supports application-aware weighting profiles.
- Supports intent-driven and composition-driven workflows.
- Uses remote LLM reasoning with deterministic physics/ML fallback.

## Project Structure

- `app.py` — Streamlit UI (Chat & Design, Composition Editor, Multi-Compare)
- `backend/app` — FastAPI backend wrapper
- `frontend/` — HTML/CSS/JS client
- `physics/` — 42-domain physics evaluator
- `core/` — elements, alloy database, data hub, query parser
- `engines/` — design pipeline, researcher, engine modes
- `llms/` — remote LLM gateway, intent parser, explainer, conversation memory
- `ml/` — ML property predictor
- `rag/` — literature retrieval enrichment
- `tests/` — unit tests

## Quick Start (API + Web)

1. Install dependencies and start API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in your API keys
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300
```

2. Run frontend:

```powershell
cd frontend
python -m http.server 5173
```

3. Open `http://localhost:5173` and keep API base as `http://localhost:8000`.

Long-running design requests target a 5-minute browser/API window. `--timeout-keep-alive 300` helps prevent idle connections from dropping.

## Streamlit Mode

```powershell
streamlit run app.py
```

## API Design

Primary endpoint:

- `POST /api/v1/run` (single orchestrator endpoint)

Utility endpoints:

- `GET /health`
- `GET /api/v1/domains`

Legacy compatibility endpoints:

- `POST /api/v1/intent/classify`
- `POST /api/v1/engine/run`
- `POST /api/v1/composition/analyze`

OpenAPI contract: `openapi.yaml`

## Remote LLM Gateway

All LLM usage routes through one deterministic gateway in `llms/client.py`:

| Priority | Provider | Model | Tier |
|----------|----------|-------|------|
| 1 | OpenRouter (fixed) | `openai/gpt-oss-20b:free` | Free |
| 2 | OpenRouter (router) | `openrouter/free` | Free |
| 3 | Gemini | `gemini-2.5-flash` | Metered |
| 4 | Groq | `llama-3.1-8b-instant` | Metered |
| 5 | xAI Grok | `grok-3-mini` | Metered |

Physics, ML scoring, ranking, and candidate generation are fully deterministic.
Remote LLMs are used for: intent parsing, application research, composition proposals, explanations, and chat.
When no API key is configured, the app falls back to rule-based intent parsing and template generation.

## Environment Variables

### Required (at least one API key)

- `OPENROUTER_API_KEY` — primary free-tier provider
- `GEMINI_API_KEY` — Google Gemini
- `GROQ_API_KEY` — Groq cloud
- `XAI_API_KEY` — xAI Grok (optional)

### LLM Configuration

- `AIDE_ENABLE_REMOTE_LLM` — `1` to enable, `0` to disable all remote calls
- `AIDE_USE_LLM_INTENT` — `1` to use LLM for intent parsing (default: `1`)
- `AIDE_USE_LLM_RESEARCH` — `1` to use LLM for application research (default: `1`)
- `AIDE_USE_LLM_GENERATION` — `1` to use LLM for composition proposals (default: `1`)
- `AIDE_OPENROUTER_MODEL` — override OpenRouter model
- `AIDE_OPENROUTER_ROUTER_MODEL` — override OpenRouter free router model
- `AIDE_GEMINI_MODEL` — override Gemini model
- `AIDE_GROQ_MODEL` — override Groq model
- `AIDE_XAI_MODEL` — override xAI model
- `AIDE_LLM_PROVIDER_ORDER` — comma-separated provider fallback order for chat
- `AIDE_LLM_JSON_PROVIDER_ORDER` — comma-separated provider fallback order for JSON tasks
- `AIDE_OPENROUTER_TITLE` — app title sent to OpenRouter
- `AIDE_OPENROUTER_REFERER` — referer header for OpenRouter
- `AIDE_LLM_HTTP_TIMEOUT_SECONDS` — HTTP timeout (default: `45`)

### API Server

- `AIDE_API_CORS_ORIGINS` — CORS allowed origins (default: `*`)
- `AIDE_PROXY_TIMEOUT_MS` — proxy timeout in milliseconds

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
