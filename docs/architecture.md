# AIDE v5 Web Architecture

## Goal
Move from Streamlit-only UI to API + web frontend while keeping Python ML/physics/LLM logic unchanged.

## Runtime Components
- `backend/app/main.py`: FastAPI app.
- `backend/app/services/analysis_service.py`: adapter layer to existing `classify_intent`, `route`, and `run_all`.
- `backend/app/services/serialization.py`: JSON-safe serialization for domain/check dataclasses.
- `frontend/`: static web client.
- Existing packages (`core`, `physics`, `engines`, `llms`, `ml`) remain source of truth.

## API Strategy
Primary orchestrator endpoint:
- `POST /api/v1/run`

Modes handled through one payload:
- Query flow: provide `query` (intent classification + engine route)
- Intent flow: provide `intent`
- Composition flow: provide `composition` + `basis`

Utility endpoints:
- `GET /health`
- `GET /api/v1/domains`

## Local LLM Strategy
- Use local model for intent parsing and explanation generation.
- Keep physics scoring and ML predictions in deterministic Python modules.
- Avoid forcing LLM to replace domain calculations.

## Migration Path
1. Keep Streamlit app active.
2. Move frontend traffic to `POST /api/v1/run`.
3. Add auth/persistence later.
4. Decommission Streamlit UI only after feature parity.

## Deployment Shape
- Backend: containerized FastAPI.
- Frontend: static hosting.
- CORS controlled by `AIDE_API_CORS_ORIGINS`.

## Deployment Assets
- deploy/backend.Dockerfile and root Dockerfile for API container deployment.
- deploy/FREE_DEPLOY.md for free-tier hosting runbook.
- deploy/prepare_hf_space.ps1 to build a Hugging Face Space bundle.
- rontend/wrangler.toml and rontend/_headers for Cloudflare Pages static hosting.

