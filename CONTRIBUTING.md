# Contributing to AIDE

Thanks for contributing.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then fill in at least one API key
streamlit run app.py
```

`.env` is local-only and must never be committed.

## Running Tests

```powershell
python -m pytest tests/ -v
```

All 32 tests must pass before committing.

## Workflow

1. Create a feature/fix branch (recommended prefix: `codex/`).
2. Make focused, reviewable changes.
3. Run `python -m pytest tests/ -v` and verify all tests pass.
4. Verify app behavior locally in the impacted tabs/flows.
5. Commit with a clear message.
6. Open a PR with scope, rationale, and validation notes.

## Validation Checklist

- App launches (`streamlit run app.py`).
- Interactive editor analysis runs end to end.
- Domain charts and tables render correctly.
- Chat & Design tab produces scored candidates for novel queries.
- Multi-Compare tab works with both preset and custom compositions.
- No secrets are committed (`.env` must stay untracked).

## Commit Guidance

- Use concise imperative messages (for example: `Improve domain coverage defaults`).
- Keep unrelated changes in separate commits when possible.
