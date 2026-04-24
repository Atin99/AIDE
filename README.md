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
- Uses local-first LLM reasoning with optional provider fallback.

## Project Structure

- `app.py` - Streamlit UI
- `backend/app` - FastAPI backend wrapper
- `frontend/` - HTML/CSS/JS client
- `physics/`, `core/`, `engines/`, `llms/`, `ml/` - existing computation stack

## Quick Start (API + Web)

1. Install dependencies and start API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300
```

2. Run frontend:

```powershell
cd frontend
python -m http.server 5173
```

3. Open `http://localhost:5173` and keep API base as `http://localhost:8000`.

Long-running design requests now target a 5-minute browser/API window. `--timeout-keep-alive 300` helps prevent idle connection reuse from dropping, but if you deploy behind another proxy you may also need that platform's read/request timeout set to 300 seconds.

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

## Local LLM First Mode

Set these in `.env`:

- `AIDE_USE_LOCAL_LLM=1`
- `AIDE_LOCAL_FIRST=1`
- `AIDE_USE_LOCAL_INTENT=1`
- `AIDE_USE_LLM_INTENT=0`
- `AIDE_LOCAL_LLM_URL=http://127.0.0.1:11434`
- `AIDE_LOCAL_LLM_MODELS=phi3:mini`
- `AIDE_ENABLE_REMOTE_LLM=0`
- `AIDE_LOCAL_INTENT_MODELS=phi3:mini`
- `AIDE_LOCAL_INTENT_MODEL_TRIES=3`

This keeps most reasoning local while Python physics/ML scoring remains deterministic.
.

## Streamlit Mode

```powershell
streamlit run app.py
```

## Environment Variables

- `GEMINI_API_KEY`
- `DEEPSEEK_API_KEY`
- `GROQ_API_KEY`
- `AIDE_GROQ_MODEL`
- `AIDE_LLM_HTTP_TIMEOUT_SECONDS`
- `AIDE_USE_LOCAL_LLM`
- `AIDE_LOCAL_FIRST`
- `AIDE_ENABLE_REMOTE_LLM`
- `AIDE_LOCAL_LLM_URL`
- `AIDE_LOCAL_LLM_MODELS`
- `AIDE_LOCAL_INTENT_MODELS`
- `AIDE_LOCAL_INTENT_MODEL_TRIES`
- `AIDE_API_CORS_ORIGINS`
- `AIDE_PROXY_TIMEOUT_MS`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).





