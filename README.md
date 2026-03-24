# AIDE v5

AIDE (Alloy Intelligence and Design Engine) is a Streamlit app for alloy analysis and design using multi-domain physics scoring, contextual weighting, and conversational workflows.

## What It Does

- Evaluates alloys across 42 physics and engineering domains.
- Computes weighted and raw composite scores with pass/warn/fail checks.
- Supports application-aware weighting profiles (structural, corrosion, high-temp, nuclear, biomedical, and more).
- Provides an interactive composition editor plus multi-alloy comparison views.
- Uses local-first LLM reasoning (Ollama) with optional API provider fallback.

## Project Structure

- `app.py` - main Streamlit UI
- `physics/` - domain models and scoring pipeline
- `core/` - composition, elements, and alloy database utilities
- `engines/` - analysis mode routing
- `llms/` - intent parsing and provider clients
- `ml/` - predictive model utilities

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies.
3. Configure environment variables.
4. Launch Streamlit.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

## Environment Variables

See `.env.example` for a ready template.

- `GEMINI_API_KEY`
- `DEEPSEEK_API_KEY`
- `GROQ_API_KEY`
- `AIDE_USE_LOCAL_LLM`
- `AIDE_LOCAL_FIRST`
- `AIDE_LOCAL_LLM_URL`
- `AIDE_LOCAL_LLM_MODELS`
- `AIDE_LOCAL_INTENT_MODELS`

## Domain Coverage Note

In the Interactive Composition Editor:

- Full 42-domain sweep is the recommended default.
- Fast subset mode is optional for speed and evaluates only top-weighted domains.
- For close-call composition comparisons, use the full 42-domain sweep.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

