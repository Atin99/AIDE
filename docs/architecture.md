# AIDE v5 Architecture

## System Overview

AIDE v5 is a physics-constrained alloy design engine with three layers:

1. **Physics Core** (deterministic) — 42-domain evaluator, element database, composition validation
2. **Design Pipeline** (deterministic + optional LLM) — candidate generation, screening, physics evaluation, scoring
3. **API Layer** — FastAPI backend serving both API endpoints and the web frontend

## Runtime Components

| Component | Path | Role |
|-----------|------|------|
| FastAPI app | `backend/app/main.py` | HTTP server, serves frontend at `/app/` |
| Analysis service | `backend/app/services/analysis_service.py` | Orchestrates intent → pipeline → response |
| Design pipeline | `engines/pipeline.py` | Multi-iteration candidate generation and evaluation |
| Application researcher | `engines/researcher.py` | Infers metallurgical constraints from queries |
| Physics evaluator | `physics/filter.py` | 42-domain scoring engine |
| LLM gateway | `llms/client.py` | Remote API provider fallback chain |
| Frontend | `frontend/` | Static HTML/JS/CSS client |
| Streamlit UI | `app.py` | Alternative interface (Chat & Design, Editor, Compare) |

## Design Pipeline Flow

```
Query → Intent Parser → Application Researcher → Candidate Generator
    → Downselection (screening) → Physics Evaluation (42 domains)
    → Scoring (composite + penalties) → Ranking → Response
```

### Scoring System

Each physics-evaluated candidate receives:

1. **Raw composite score** from `run_all()` — weighted average of 42 domain scores
2. **Base element penalty** — proportional (0.1–1.0) for shortfall vs requirement
3. **Mechanism check** — validates mandatory mechanisms (γ', solid solution, etc.)
4. **Domain-weighted blending** — primary domains get higher weight
5. **Overalloying penalty** — exponential decay for excessive solute count
6. **Application alignment** — multiplier for application-specific composition matching
7. **Constraint enforcement** — density, cost, element inclusion/exclusion

**Design principle:** Proportional penalties everywhere. Only drastically wrong compositions (base element < 20% of requirement) get hard-rejected. Everything else gets scored proportionally.

## LLM Strategy

- All LLM usage is remote-only via `llms/client.py` gateway.
- Free-first provider ordering: OpenRouter → Gemini → Groq → xAI.
- LLMs handle: intent parsing, application research, composition proposals, explanations, chat.
- Physics scoring, ML predictions, and candidate ranking are fully deterministic.
- When no API key is configured, rule-based fallback handles all paths.

## API Design

Single orchestrator endpoint: `POST /api/v1/run`

Modes determined by payload:
- **Query flow:** `{query: "..."}` → intent classification → engine route
- **Composition flow:** `{composition: {...}, basis: "wt"}` → direct physics evaluation
- **Alloy lookup:** query matches known alloy name → catalog entry + physics evaluation

Response includes:
- `candidates_detail` — only physics-evaluated candidates (screen-only filtered out)
- `generation_stats` — raw/dedupe/downselect/physics counts per iteration
- `thinking_steps` — pipeline reasoning trace

## Deployment

### Render (Production)

- `render.yaml` configures auto-deploy from `main` branch
- Backend defaults: 1 iteration (~11s), ML disabled
- Free-tier constraint: 30s request timeout

### Hugging Face Spaces

- `Dockerfile` for Streamlit mode on port 7860

### Local Development

- `uvicorn backend.app.main:app --port 9000` for API + frontend
- `streamlit run app.py` for Streamlit mode
