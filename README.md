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

AIDE (Alloy Intelligence and Design Engine) is a physics-constrained alloy design platform. It generates, evaluates, and ranks candidate alloy compositions across 42 engineering domains using deterministic physics models, with optional remote LLM reasoning for intent parsing and research.

## What It Does

- **42-Domain Physics Evaluation** — thermodynamic, mechanical, corrosion, fatigue, creep, weldability, and 36 more domain checks on every candidate.
- **Iterative Design Pipeline** — generates candidate compositions, evaluates with full physics, ranks by weighted composite score, and iterates with feedback.
- **Proportional Scoring** — candidates receive proportional penalties for base element shortfalls and application misalignment instead of hard rejections.
- **Application-Aware Constraints** — the researcher infers metallurgical constraints (base elements, mechanisms, forbidden elements) from the query and applies them to generation and scoring.
- **Remote LLM Gateway** — optional LLM reasoning for intent parsing, application research, and composition proposals via free-tier API providers.
- **Multiple Interfaces** — FastAPI backend + HTML/JS frontend, Streamlit UI, or direct API.

## Project Structure

- `backend/app/` — FastAPI backend (API routes, services, main entry point)
- `frontend/` — HTML/CSS/JS client (single-page app with engine run, composition editor, multi-compare)
- `physics/` — 42-domain physics evaluator (`filter.py`, domain modules)
- `engines/` — design pipeline (`pipeline.py`), application researcher (`researcher.py`), engine modes
- `core/` — elements database, alloy catalog, data hub, query parser
- `llms/` — remote LLM gateway (`client.py`), intent parser, explainer, conversation memory
- `ml/` — ML property predictor (XGBoost/scikit-learn)
- `rag/` — literature retrieval enrichment
- `app.py` — Streamlit UI (Chat & Design, Composition Editor, Multi-Compare)
- `tests/` — unit tests (32 tests covering pipeline, scoring, intent, and query behaviors)

## Quick Start (API + Frontend)

1. Install dependencies and start API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in your API keys
uvicorn backend.app.main:app --host 0.0.0.0 --port 9000 --timeout-keep-alive 300
```

2. Open `http://localhost:9000/app/` — the frontend is served directly by the backend.

Long-running design requests may take 10-30 seconds depending on iteration count.

## Streamlit Mode

```powershell
streamlit run app.py
```

## API Design

Primary endpoint:

- `POST /api/v1/run` — unified orchestrator (design engine, composition analysis, alloy lookup)

Utility endpoints:

- `GET /health`
- `GET /api/v1/domains`
- `GET /api/v1/alloys`

Legacy compatibility endpoints:

- `POST /api/v1/intent/classify`
- `POST /api/v1/engine/run`
- `POST /api/v1/composition/analyze`

OpenAPI contract: `openapi.yaml`

## Scoring & Ranking

Each candidate receives a composite score (0-100) computed as:

1. **Physics composite** — weighted average across 42 domains (each domain runs multiple checks with pass/warn/fail thresholds).
2. **Application alignment** — multiplier (0.1-1.0) based on how well the composition matches the target application family.
3. **Overalloying penalty** — reduces scores for compositions with excessive solute additions.
4. **Base element penalty** — proportional penalty when base element fraction falls below the target (not a hard rejection).
5. **Constraint enforcement** — density, cost, and element inclusion/exclusion constraints.

Only physics-evaluated candidates appear in results. Screen-only candidates (heuristic scores) are internal pipeline artifacts and are not shown to users.

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
- `AIDE_GEMINI_MODEL` — override Gemini model
- `AIDE_GROQ_MODEL` — override Groq model
- `AIDE_XAI_MODEL` — override xAI model
- `AIDE_LLM_PROVIDER_ORDER` — comma-separated provider fallback order for chat
- `AIDE_LLM_JSON_PROVIDER_ORDER` — comma-separated provider fallback order for JSON tasks
- `AIDE_LLM_HTTP_TIMEOUT_SECONDS` — HTTP timeout (default: `45`)

### API Server

- `AIDE_API_CORS_ORIGINS` — CORS allowed origins (default: `*`)

## Deployment

### Render

Configured via `render.yaml`. Auto-deploys from `main` branch.
Backend defaults: 1 iteration, ML disabled (fits within free-tier 30s timeout).
Frontend overrides can request more iterations if needed.

### Hugging Face Spaces

Configured via `Dockerfile`. Uses Streamlit mode on port 7860.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
