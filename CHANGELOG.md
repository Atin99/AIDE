# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

- Remote LLM gateway with stable free-first provider fallback chain (OpenRouter → Gemini → Groq → xAI).
- LLM-first intent parsing with rule-based guardrails and deterministic fallback.
- LLM-assisted application research and composition proposal in the design pipeline.
- Intent Workbench feature plan (`docs/INTENT_WORKBENCH_PLAN.md`).
- Custom composition comparison in Multi-Compare tab — compare any user-entered compositions alongside preset alloys.
- Property-based heat-spreader and thermal-conductive application classification.
- Canonical property vocabulary guardrails for LLM intent output.
- Element symbol normalization (handles lowercase `ti` → `Ti` from LLMs).
- Numeric constraint coercion (handles string values like `"2.7 g/cm3"` from LLMs).
- RAG agent fix for stale import path.
- Unit tests for provider ordering, query behaviors, pipeline iteration pool, and RAG module.

### Changed

- All LLM usage is now remote-only via API providers. Removed Ollama/local LLM support.
- Provider rotation replaced with deterministic free-first fallback chain.
- Intent parser now merges LLM output with rule-based parsing instead of using either alone.
- Interactive Composition Editor defaults to full 42-domain sweep.
- Fast subset mode is explicitly opt-in with clearer labeling.

### Fixed

- `hea` keyword matching no longer triggers on words like `heat` or `heat spreader`.
- Rocket chamber / combustion liner queries now correctly map to superalloy context.
- Pipeline research constraints are properly propagated to generation and scoring.
- Reduced risk of silently excluding low-weight domains during close-composition comparisons.
