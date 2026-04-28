# Changelog

All notable changes to this project will be documented in this file.

## v5.4 — 2026-04-28

### Fixed (Scoring Overhaul)

- **Eliminated 0.0 score bug** — `composition_violates_base()` was hard-rejecting any candidate below 95% of base element requirement. Changed to proportional penalty (only hard-reject below 20% of requirement).
- **Fixed double-rejection** — `_application_alignment()` was independently re-checking base element compliance and returning 0.0 alignment multiplier, zeroing scores even after the main evaluation passed.
- **Fixed thermal penalty misfire** — `_overalloying_penalty()` matched "thermal" in "thermal management" and applied the extreme conductor penalty (`exp(-7x)`) to superalloy/heat-exchanger queries. Added exclusion for superalloy/turbine/jet queries.
- **Hidden screen-only candidates** — `candidates_detail` API response now only includes physics-evaluated candidates. Screen-only candidates (heuristic scores) were confusing users with inflated scores.
- **Fixed frontend iteration override** — `frontend/app.js` was hardcoding `max_iterations: 4, use_ml: true` as overrides, bypassing backend timeout defaults and causing Render 30s timeout.

### Added

- `ResearchResult.base_element_penalty()` — proportional penalty factor (0.0–1.0) for base element shortfalls, replacing the hard binary rejection.
- Proportional scoring pipeline: base element shortfall, overalloying, and alignment all apply smooth multipliers instead of hard zeros.

### Changed

- Backend defaults: `max_iterations=1`, `min_iterations=1`, `use_ml=false` — fits within Render free-tier 30s timeout (~11s per run).
- Frontend engine run: `max_iterations=1`, `use_ml=false` — consistent with backend defaults.

## v5.3 — 2026-04-28

### Fixed (Composition Quality)

- Stainless steel queries now correctly enforce Nickel inclusion (8% for stainless, 10% for marine, 5% for duplex).
- Default seeds updated to industry-standard benchmarks (316L for stainless, IN718 for superalloys).
- Alignment scoring penalizes Ni-free marine alloys (0.35x) and rewards Molybdenum for corrosion resistance.

### Added

- Custom composition entry in Multi-Compare tab — inject arbitrary alloy formulations and compare against database alloys.
- Remote LLM gateway with free-first provider fallback (OpenRouter → Gemini → Groq → xAI).
- Intent Workbench feature plan (`docs/INTENT_WORKBENCH_PLAN.md`).

### Changed

- **Remote-only LLM architecture** — removed all Ollama/local model support. All LLM usage via remote API providers.
- Deterministic free-first provider fallback replaces provider rotation.

### Removed

- Ollama integration and local LLM runtime.
- Legacy codex feature branches (consolidated to `main`).

## v5.2 — Earlier

### Added

- 42-domain physics evaluator.
- Multi-iteration design pipeline with feedback loop.
- Application researcher with heuristic and LLM-powered constraint inference.
- ML property predictor integration.
- RAG literature retrieval enrichment.
- Streamlit and FastAPI dual-interface support.
