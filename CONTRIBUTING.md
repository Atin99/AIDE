# Contributing to AIDE

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then fill in at least one API key
```

`.env` is local-only and must never be committed.

### Run backend + frontend

```powershell
uvicorn backend.app.main:app --host 0.0.0.0 --port 9000 --timeout-keep-alive 300
```

Open `http://localhost:9000/app/`

### Run Streamlit

```powershell
streamlit run app.py
```

## Running Tests

```powershell
python -m pytest tests/ -v
```

All 32 tests must pass before committing.

## Key Files

| File | Purpose |
|------|---------|
| `engines/pipeline.py` | Core design pipeline — candidate generation, physics evaluation, scoring |
| `engines/researcher.py` | Application research — infers metallurgical constraints from queries |
| `engines/modes.py` | Engine modes — routes intents to design/modify/study/compare engines |
| `physics/filter.py` | 42-domain physics evaluator |
| `llms/client.py` | Remote LLM gateway with provider fallback |
| `backend/app/services/analysis_service.py` | Backend service layer — orchestrates intent → pipeline → response |
| `frontend/app.js` | Frontend application logic |

## Scoring Architecture

Scoring uses **proportional penalties**, not hard rejections:

- Base element shortfall → proportional multiplier (0.1–1.0)
- Overalloying → exponential decay based on solute count
- Application mismatch → proportional alignment multiplier
- Only drastically wrong compositions (base element below 20% of requirement) get hard-rejected

## Workflow

1. Create a feature branch from `main`.
2. Make focused, reviewable changes.
3. Run `python -m pytest tests/ -v` — all 32 tests must pass.
4. Verify app behavior locally on the impacted flows.
5. Commit with a clear imperative message.
6. Push to `main` (or open a PR for review).

## Validation Checklist

- Backend starts (`uvicorn backend.app.main:app`).
- Frontend loads at `/app/`.
- Engine run produces scored candidates for novel queries (no 0.0 scores for valid compositions).
- Composition editor analysis runs end to end with domain charts.
- Multi-Compare tab works with both preset and custom compositions.
- No secrets committed (`.env` must stay untracked).
