# AIDE v5 Full Project Report

## 1. Executive Summary

AIDE v5 stands for **Alloy Intelligence and Design Engine**. It is a multi-layer alloy design and analysis platform that combines:

- a curated alloy database,
- an element property database,
- a natural-language intent parser,
- a multi-mode orchestration layer,
- a 42-domain physics and heuristics scoring engine,
- optional ML, RAG, and web-enrichment modules,
- a FastAPI backend,
- a static web frontend,
- and a legacy but still useful Streamlit interface.

In simple words, AIDE v5 is a system that lets a user ask for an alloy in natural language, analyze an existing composition, compare known alloys, study tradeoffs, and get structured explanations for why one composition is more suitable than another.

The most important conclusion from my study is this:

**AIDE v5 behaves more like an intent-conditioned alloy evaluation platform than a pure black-box predictor.** The system is strongest when the user clearly states the target application and desired properties, because application and weight-profile choices influence results much more than secondary context like environment or process.

---

## 2. What This Project Is

AIDE v5 is not just one script. It is a full project with three major layers:

1. **User interfaces**
   - `frontend/` provides the browser UI.
   - `app.py` provides the Streamlit UI.

2. **Orchestration and reasoning**
   - `backend/app/` exposes the engine as an API.
   - `llms/`, `engines/`, and `core/` decide what the user wants and how to search for candidate alloys.

3. **Evaluation and intelligence**
   - `physics/` scores each alloy across 42 domains.
   - `ml/` predicts material properties when ML is enabled.
   - `rag/`, `web/`, `engineering/`, and `explainability/` enrich the system.

So the project is best understood as a **materials design platform**, not only a UI, not only a model, and not only a database.

---

## 3. What AIDE v5 Does

AIDE v5 supports several practical workflows:

- **Design mode**: create new alloy candidates from a natural-language goal.
- **Modify mode**: start from an existing alloy and adjust it toward new constraints.
- **Study mode**: deeply analyze a single alloy or composition.
- **Compare mode**: compare two alloys across all supported domains.
- **Explore mode**: inspect alloy families and candidate spaces.
- **Geometry mode**: connect alloy properties to engineering calculations.
- **Chat mode**: conversational support around alloy design.
- **Direct composition analysis**: evaluate a user-entered composition immediately without running the full design pipeline.

The system can answer questions like:

- "Design a corrosion resistant stainless alloy."
- "Create a low melting lead-free fuse alloy."
- "Compare 316L and 2205."
- "Analyze this Fe-Cr-Ni-Mo composition."
- "Find a high-temperature alloy for turbine service."

---

## 4. High-Level Architecture

### 4.1 End-to-End Flow

```text
User
  -> frontend/app.js or app.py
  -> backend/app/main.py (API) or direct local calls from Streamlit
  -> backend/app/services/analysis_service.py
  -> llms/intent_parser.py
  -> engines/modes.py
     -> DesignEngine / ModifyEngine / StudyEngine / CompareEngine / ExploreEngine / GeometryEngine / ChatEngine
     -> for design work: engines/pipeline.py
        -> engines/researcher.py
        -> core/generator.py
        -> core/query_parser.py
        -> core/alloy_db.py and core/elements.py
        -> optional ml/predict.py
        -> physics/filter.py
           -> 42 physics domain modules
        -> llms/explainer.py
  -> backend/app/services/serialization.py
  -> JSON response
  -> frontend charts/tables or Streamlit charts/tables
```

### 4.2 Two Important Execution Paths

**Path A: Natural-language design request**

1. The query comes in through the API or Streamlit UI.
2. `llms/intent_parser.py` extracts mode, application, properties, constraints, and composition hints.
3. `engines/modes.py` selects the correct engine.
4. In design mode, `engines/pipeline.py` generates, filters, scores, and explains candidate alloys.
5. `physics/filter.py` evaluates each candidate across all domains.
6. The best candidates and explanations are returned to the UI.

**Path B: Direct composition analysis**

1. The user provides an explicit composition.
2. `backend/app/services/analysis_service.py` or `app.py` sends it directly to `physics/filter.py`.
3. `run_all(...)` evaluates the composition across domains.
4. Results, checks, and explanations are shown without needing the full generation pipeline.

---

## 5. Simplified File Structure

```text
aide v5/
  app.py
  generate_aide_datasets.py
  START_AIDE.ps1
  START_AIDE.bat
  openapi.yaml
  render.yaml
  backend/
  core/
  engines/
  llms/
  physics/
  ml/
  optimisation/
  rag/
  engineering/
  explainability/
  web/
  frontend/
  dataset_exports/
  docs/
  deploy/
  tests/
```

### 5.1 What Each Top-Level Folder Means

| Folder | Purpose |
| --- | --- |
| `backend/` | FastAPI service layer exposing AIDE as an API |
| `core/` | Alloy database, element database, query parsing, candidate generation |
| `engines/` | Workflow routing and design/search pipeline |
| `llms/` | Intent parsing, provider routing, explanations, memory |
| `physics/` | Main domain scoring system |
| `ml/` | Feature extraction, surrogate models, ensemble prediction, training |
| `optimisation/` | Pareto and Bayesian optimization support |
| `rag/` | Literature retrieval and explanation support |
| `engineering/` | Engineering calculations using geometry/loading context |
| `explainability/` | SHAP-based interpretation utilities |
| `web/` | Best-effort online lookup and scraping helpers |
| `frontend/` | Browser UI, charts, proxy, deployment config |
| `dataset_exports/` | Generated datasets and manifests |
| `docs/` | Project documentation |
| `deploy/` | Deployment helpers and Hugging Face packaging mirror |
| `tests/` | Query/pipeline tests outside backend smoke tests |

### 5.2 Important Non-Primary Trees

- `deploy/hf_space_bundle/` is a **deployment mirror** of the main runtime packages for Hugging Face style deployment. It duplicates logic already present in the main tree, so it should not be treated as a second architecture.
- `aide_fix_extracted/aide_fix/engines/pipeline.py` appears to be an **extracted artifact** or scratch copy. I found no references to it in the live code paths.
- `dataset_exports/` contains **generated outputs**, not source code.

---
## 6. File-by-File Guide

Before the detailed file list, one note:

- The many `__init__.py` files in `backend/app`, `backend/app/services`, `backend/tests`, `core`, `engines`, `engineering`, `explainability`, `llms`, `ml`, `optimisation`, `physics`, `rag`, and `web` mainly serve as **package markers**. They do not contain the main application logic.

### 6.1 Root-Level Runtime and Project Files

| File | What It Does | How It Connects |
| --- | --- | --- |
| `app.py` | Legacy Streamlit application with chat, composition editor, comparison tools, charts, and downloadable text report generation. | Calls `classify_intent`, `route`, and `run_all` directly. It is a full local UI that can operate without the browser frontend. |
| `generate_aide_datasets.py` | Creates structured datasets for catalogs, application sweeps, profile sweeps, comparisons, and intent scenarios. | Uses the live alloy database and live scoring engine, so it is a very good system-level testing tool. |
| `START_AIDE.ps1` | Preferred Windows launcher for the backend. It chooses a virtual environment, installs missing API dependencies if needed, clears stale port use, and runs Uvicorn. | Starts `backend.app.main:app`. |
| `START_AIDE.bat` | Batch wrapper around the PowerShell launcher. | Convenience launcher for Windows users. |
| `Dockerfile` | Container setup for running the backend service. | Packages the backend for deployment. |
| `openapi.yaml` | API contract for the service. | Documents the FastAPI interface. |
| `render.yaml` | Render deployment configuration. | Describes hosted service settings. |
| `README.md` | Main project overview and usage description. | High-level entry document for the repo. |
| `CHANGELOG.md` | Change history. | Useful for project evolution tracking. |

### 6.2 Backend Files

| File | What It Does | How It Connects |
| --- | --- | --- |
| `backend/app/main.py` | FastAPI entrypoint. Defines health, alloy list, domain list, unified run, intent classify, engine run, and composition analyze endpoints. Also serves the frontend under `/app/...`. | Calls `analysis_service.py`, wraps everything in API responses, and is the main server process. |
| `backend/app/schemas.py` | Pydantic models for request/response payloads and override fields. | Enforces structured data exchange for the API layer. |
| `backend/app/services/analysis_service.py` | Core backend adapter. Loads env, lists alloys/domains, classifies queries, runs engines, runs direct composition analysis, and decides whether a payload is a query run or composition run. | Bridges API payloads to `llms.intent_parser`, `engines.modes.route`, `physics.filter.run_all`, and `core.alloy_db`. |
| `backend/app/services/serialization.py` | Converts `Check`, `DomainResult`, and nested runtime objects into JSON-safe structures. | Makes the physics and engine outputs safe for API responses. |
| `backend/tests/test_api.py` | API smoke tests for root, health, domains, unified engine run, unified composition run, and error behavior. | Verifies the backend entrypoints. |
| `backend/requirements.api.txt` | Backend dependency list. | Used by launchers and deployment. |
| `backend/README.md` | Backend-specific API documentation. | Supports backend usage and deployment understanding. |

### 6.3 Frontend Files

| File | What It Does | How It Connects |
| --- | --- | --- |
| `frontend/index.html` | Main web UI shell with tabs for engine runs, composition editing, and multi-compare. | Loads the frontend scripts and styles and talks to the backend API. |
| `frontend/app.js` | Frontend logic for health checks, alloy loading, query submission, composition editor, compare tools, charts, and result rendering. | Calls `/api/v1/...` endpoints and turns responses into interactive visual output. |
| `frontend/styles.css` | Main styling for the browser UI. | Gives the frontend its current visual system. |
| `frontend/functions/api/[[path]].js` | Cloudflare Pages function that proxies frontend API traffic to the backend. | Important for deployment when frontend and backend are separated. |
| `frontend/wrangler.toml` | Cloudflare deployment config. | Supports frontend hosting. |
| `frontend/_headers` | Security and caching headers. | Hardens frontend deployment. |
| `frontend/README.md` | Frontend-specific notes. | Explains browser UI setup and deployment. |

### 6.4 Core Files

| File | What It Does | How It Connects |
| --- | --- | --- |
| `core/elements.py` | Defines the elemental property database and composition validation helpers. | Used everywhere properties are computed from elemental makeup. |
| `core/alloy_db.py` | Stores the named alloy library with aliases, categories, applications, and known properties. | Used by intent resolution, baseline prediction, comparisons, UI alloy lists, and dataset generation. |
| `core/query_parser.py` | Rule-based parsing of must-have elements, excluded elements, temperature hints, PREN targets, element counts, and application clues. | Feeds structured constraints into the intent parser and generator. |
| `core/generator.py` | Heuristic composition generator. Perturbs known seeds, injects or drops minor elements, samples family-aware compositions, and respects inclusion/exclusion constraints. | Supplies raw candidate compositions to the design pipeline. |
| `core/data_hub.py` | Lazy integration facade over alloy DB, ML predictor, RAG, scraper, and cost estimation. | Designed as a shared access layer for enrichment and future consolidation. |

### 6.5 Engine Files

| File | What It Does | How It Connects |
| --- | --- | --- |
| `engines/modes.py` | Defines `DesignEngine`, `ModifyEngine`, `StudyEngine`, `CompareEngine`, `ExploreEngine`, `GeometryEngine`, and `ChatEngine`, plus the `route(...)` dispatcher. | The main router from parsed intent to the correct workflow. |
| `engines/pipeline.py` | The most important orchestration file for design mode. It handles baselines, intent conditioning, candidate generation, LLM fallback generation, de-duplication, optional ML prefiltering, downselection, full physics scoring, constraints, correlation insights, and final explanations. | This is the heart of alloy generation and ranking. |
| `engines/researcher.py` | Builds application-specific guidance such as mandatory mechanisms, forbidden elements, required domains, and domain weights. Has LLM path plus heuristic fallback. | Strengthens intent before candidate generation and scoring. |

### 6.6 LLM and Language Reasoning Files

| File | What It Does | How It Connects |
| --- | --- | --- |
| `llms/intent_parser.py` | Converts natural language into structured intent: mode, application, target properties, explicit composition, exclusions, family hints, compare/modify/study/geometry signals, and more. | This is the natural-language gateway to the whole platform. |
| `llms/client.py` | Provider router for local and remote LLMs, with JSON extraction and repair helpers. | Used when the system needs LLM assistance for parsing or explanation. |
| `llms/explainer.py` | Produces narrative explanations for results, candidates, comparisons, and single-domain behavior. Includes template fallback. | Converts numeric outputs into human-readable insight. |
| `llms/conversation_memory.py` | Maintains conversational memory for interactive sessions. | Used mainly by the Streamlit chat experience. |
| `llms/groq_client.py` | Older provider-specific client kept alongside the generic client layer. | Optional external provider support. |

### 6.7 Physics Core Files

| File | What It Does | How It Connects |
| --- | --- | --- |
| `physics/base.py` | Shared scoring math, normalization, conversion helpers, alloy descriptors such as VEC and PREN, plus the `Check` and `DomainResult` types. | Every domain module depends on this file. |
| `physics/filter.py` | Runs all domains, applies application and profile weights, aggregates pass/warn/fail behavior, and returns overall composite scores. | This is the central evaluator used by both direct analysis and the design pipeline. |
| `physics/domain_graph.py` | Defines domain relationships, groups, and cascade helpers. | Supports weighting logic and interpretation of related failures. |
| `physics/ici.py` | Implements the India Corrosion Index using environmental presets such as Mumbai coastal, Chennai coastal, Kolkata coastal, Delhi inland, and offshore Arabian conditions. | Adds region-aware corrosion context to scoring. |

### 6.8 Physics Domain Files

All of these domain files follow the same broad pattern: accept a composition and context, compute domain-specific heuristics or formulas, and return a `DomainResult`.

| File | Main Responsibility |
| --- | --- |
| `physics/acoustic.py` | Acoustic suitability and damping-related behavior. |
| `physics/biocompatibility.py` | Implant/body-contact suitability and toxic-element screening. |
| `physics/calphad_stability.py` | Thermodynamic stability via CALPHAD-style database availability and heuristics. |
| `physics/castability.py` | Casting suitability and casting-related processing behavior. |
| `physics/catalysis.py` | Catalytic suitability. |
| `physics/corrosion.py` | Corrosion resistance under environment context. |
| `physics/creep.py` | High-temperature creep resistance. |
| `physics/diffusion.py` | Diffusion-related behavior at temperature. |
| `physics/electronic_structure.py` | Electronics-relevant structure heuristics. |
| `physics/fatigue.py` | Fatigue and fracture-related behavior. |
| `physics/grain_boundary.py` | Grain boundary stability and segregation tendencies. |
| `physics/hume_rothery.py` | Hume-Rothery compatibility style checks. |
| `physics/hydrogen.py` | Hydrogen embrittlement susceptibility. |
| `physics/hydrogen_storage.py` | Hydrogen storage relevance. |
| `physics/machinability.py` | Machining friendliness. |
| `physics/magnetic.py` | Magnetic behavior. |
| `physics/mechanical.py` | Baseline mechanical performance scoring. |
| `physics/new_domains.py` | Houses seven callable domain classes: Formability, Additive Manufacturing, Heat Treatment Response, Fracture Mechanics, Impact Toughness, Galvanic Compatibility, and Solidification. |
| `physics/nuclear_fuel.py` | Nuclear fuel compatibility. |
| `physics/optical.py` | Optical-property suitability. |
| `physics/oxidation.py` | Oxidation resistance, especially at elevated temperature. |
| `physics/phase_stability.py` | General phase stability. |
| `physics/plasticity.py` | Deformation and plasticity behavior. |
| `physics/radiation.py` | Radiation resistance and irradiation behavior. |
| `physics/regulatory.py` | Safety and regulatory suitability, especially for biomedical-style constraints. |
| `physics/relativistic.py` | Heavy-element relativistic-effect heuristics. |
| `physics/shape_memory.py` | Shape-memory relevance. |
| `physics/structural_efficiency.py` | Strength-to-weight and section-efficiency style scoring. |
| `physics/superconductivity.py` | Superconducting relevance. |
| `physics/surface_energy.py` | Surface energy behavior. |
| `physics/thermal.py` | Thermal-property behavior. |
| `physics/thermo.py` | Thermodynamics and mixing-based stability indicators. |
| `physics/transformation_kinetics.py` | Process-sensitive transformation behavior, martensitic heuristics, and related kinetics. |
| `physics/tribology.py` | Wear and tribology behavior. |
| `physics/weldability.py` | Weldability and section-thickness sensitivity. |

### 6.9 ML Files

| File | What It Does | How It Connects |
| --- | --- | --- |
| `ml/features.py` | Extracts feature vectors from compositions using elemental properties and engineered descriptors. | Used before model prediction and training. |
| `ml/predict.py` | Defines the `FullModelEnsemble` and runtime predictor access. | Supplies optional ML estimates to the design pipeline. |
| `ml/multitask_net.py` | PyTorch multitask network for selected property predictions. | One component of the ML stack. |
| `ml/transfer_learning.py` | Fine-tunes model heads for experimental targets like yield and tensile properties. | Extends the ML stack into experimental-property space. |
| `ml/gp_surrogate.py` | Gaussian process surrogate and uncertainty estimation. | Supports uncertainty-aware predictions and optimization. |
| `ml/additional_models.py` | Extra regressors such as RF, ExtraTrees, LightGBM, Ridge, KNN, SVR, AdaBoost, Lasso, and ElasticNet. | Broadens the model toolbox. |
| `ml/train.py` | Training pipeline for JARVIS and Materials Project style data. | Builds model assets used by prediction components. |
| `ml/AIDE_Train.ipynb` | Notebook-based training and experimentation workspace. | More exploratory than the runtime modules. |

### 6.10 Optimization, RAG, Engineering, Web, and Explainability Files

| File | What It Does | How It Connects |
| --- | --- | --- |
| `optimisation/pareto.py` | Pareto filtering for multi-objective tradeoffs. | Useful when multiple objectives must be balanced. |
| `optimisation/bayesian_opt.py` | Bayesian optimization helpers. | Search acceleration for expensive evaluation loops. |
| `optimisation/active_learning.py` | Uncertainty-driven candidate suggestion. | Supports experiment selection and learning loops. |
| `rag/retriever.py` | Retrieves relevant indexed materials literature chunks. | Supports evidence-aware reasoning. |
| `rag/index_papers.py` | Chunks PDFs and builds the vector index. | Prepares literature for retrieval. |
| `rag/agent.py` | Uses retrieved context to generate explanations and reasoning support. | Connects literature to user-facing responses. |
| `engineering/calculations.py` | Stress, buckling, thermal stress, heat transfer, fatigue, crack size, natural frequency, and full engineering analysis. | Used by geometry-focused workflows. |
| `web/scraper.py` | Cache-backed Wikipedia and Materials Project lookup plus composition extraction and summarization. | Supplies best-effort external context when needed. |
| `explainability/shap_explain.py` | SHAP explanation helpers for XGBoost-style predictions. | Explains why an ML model produced a result. |

### 6.11 Test, Documentation, and Deployment Support Files

| File | What It Does |
| --- | --- |
| `tests/test_query_behaviors.py` | Verifies that important queries map to the expected application intent and that pipeline outputs respect family constraints. |
| `docs/architecture.md` | Existing architecture notes for the repo. |
| `deploy/run_local.ps1` | Deployment-oriented local runner. |
| `deploy/prepare_hf_space.ps1` | Prepares Hugging Face deployment bundle. |
| `deploy/backend.Dockerfile` | Alternate backend container recipe. |
| `deploy/FREE_DEPLOY.md` | Deployment instructions. |
| `deploy/hf_space_README.md` | Notes for the deployment bundle. |

---

## 7. How the Main Code Files Are Connected

### 7.1 Query-Driven Design Connection Map

1. `frontend/app.js` or `app.py` accepts the user request.
2. `backend/app/main.py` receives the request through `/api/v1/run` or another endpoint.
3. `backend/app/services/analysis_service.py` determines whether this is an engine run or direct composition analysis.
4. `llms/intent_parser.py` translates the query into structured intent.
5. `engines/modes.py` routes that intent to the right engine.
6. If it is a design task, `engines/pipeline.py` becomes the main orchestrator.
7. `engines/researcher.py` refines application constraints and domain priorities.
8. `core/generator.py` produces candidate compositions, seeded by known alloy families from `core/alloy_db.py`.
9. If enabled, `ml/predict.py` helps prefilter candidates.
10. `physics/filter.py` evaluates each candidate across all domains.
11. The individual domain files return `DomainResult` objects to the filter.
12. `llms/explainer.py` turns the numeric outcome into narrative rationale.
13. `backend/app/services/serialization.py` converts runtime objects into JSON-safe structures.
14. `frontend/app.js` or `app.py` renders tables, charts, and explanations.

### 7.2 Direct Composition Analysis Connection Map

1. The user sends a named alloy or explicit element fractions.
2. `analysis_service.py` recognizes that no search pipeline is required.
3. `core/alloy_db.py` may resolve a named alloy to a stored composition.
4. `physics/filter.py` calls all domains directly.
5. Results are serialized and returned to the UI.

### 7.3 Why This Design Is Good

This structure is strong because:

- UI is separated from evaluation logic.
- backend and Streamlit can both use the same engine core.
- physics modules are modular and individually swappable.
- ML is optional, not mandatory.
- language-model features enhance the engine but do not fully control it.

---

## 8. Dataset Generation and What I Tested

To understand the project deeply, I treated AIDE v5 as an experimental platform and generated structured datasets with `generate_aide_datasets.py`.

### 8.1 Datasets Produced

| Dataset | Rows | Purpose |
| --- | --- | --- |
| `aide_alloys_catalog.csv` | 78 | Named alloy catalog |
| `aide_elements_catalog.csv` | 88 | Element catalog |
| `aide_domains_catalog.csv` | 42 | Domain catalog |
| `aide_applications_catalog.csv` | 15 | Application catalog |
| `aide_weight_profiles_catalog.csv` | 10 | Weight profile catalog including `auto` |
| `aide_intent_scenarios.csv` | 96 | Intent-classification benchmark prompts |
| `aide_alloy_application_sweep` | 23,400 | Alloys x applications x environments x processes |
| `aide_alloy_profile_sweep` | 14,040 | Alloys x profiles x environments x processes |
| `aide_alloy_comparison` | 3,003 | All pairwise alloy comparisons |

### 8.2 How Those Counts Were Formed

- Application sweep: `78 alloys x 15 applications x 5 environments x 4 processes = 23,400`
- Profile sweep: `78 alloys x 9 explicit profiles x 5 environments x 4 processes = 14,040`
- Comparison sweep: `78 choose 2 = 3,003`

### 8.3 Execution Quality

The full suite manifest reports:

- total generation time: **448.203 seconds**
- application sweep failures: **0**
- profile sweep failures: **0**
- comparison sweep failures: **0**

This is important because it shows the live evaluation engine can be exercised at scale without collapsing under its own edge cases.

### 8.4 What I Was Testing Through the Datasets

By generating these datasets, I was effectively testing:

- how stable scores are across environments and processes,
- how strongly application intent changes the ranking,
- how strongly weight profiles change the ranking,
- whether similar alloy families remain near each other,
- which domains actually discriminate between alloys,
- and whether the parser and pipeline behave consistently across repeated structured scenarios.

---
## 9. My Observations From the Dataset Study

### 9.1 The Biggest Special Observation

The single most important thing I observed is:

**AIDE v5 is much more sensitive to design intent than to mild context changes.**

Average score swing for the same alloy under different conditions:

| Type of change | Average score range |
| --- | --- |
| Application change | 2.9364 |
| Weight-profile change | 3.4982 |
| Environment change | 0.2327 |
| Process change | 0.0928 |

This means:

- the question the user asks matters a lot,
- the chosen weight profile matters a lot,
- but environment and process currently move the final score much less on average.

So the current engine behaves more like an **intent-prioritized ranking system** than a deeply environment-driven simulator.

### 9.2 Overall Score Behavior

For the application sweep:

- mean composite score: **62.753**
- minimum score: **56.538**
- maximum score: **69.463**

For the profile sweep:

- mean composite score: **62.792**

This tells me the engine generally works in a fairly narrow scoring band. It ranks materials meaningfully, but the score spread is not extremely wide. That is useful for relative comparison, but it also suggests there may still be headroom to improve calibration and separation power.

### 9.3 Applications That Score Highest and Lowest

Highest average application contexts:

- `refractory`: **64.029**
- `stainless`: **63.668**
- `superalloy`: **63.668**
- `biomedical`: **63.460**
- `nuclear`: **63.366**

Lowest average application contexts:

- `cu_alloy`: **61.741**
- `electronic_alloy`: **61.741**
- `fusible_alloy`: **62.126**
- `general_structural`: **62.126**
- `hea`: **62.126**

Interpretation:

- high-temperature and corrosion-aware contexts currently score slightly better overall,
- electronic and fusible contexts seem harder under the present rule set,
- and the engine currently appears especially comfortable in structural/corrosion/high-temperature spaces.

### 9.4 Weight Profiles Matter a Lot

Highest average profile scores:

- `high_temp`: **64.029**
- `nuclear`: **63.645**
- `biomedical`: **63.554**
- `manufacturing`: **62.905**
- `structural`: **62.779**

Lowest average profile scores:

- `conductive`: **61.741**
- `catalysis`: **61.908**
- `balanced`: **62.126**

The strongest profile swings included:

- `2507` in `delhi_inland`, `annealed`: worst `conductive` **63.274**, best `corrosion` **68.652**, swing **5.378**
- `2507` in `delhi_inland`, `cold_worked`: swing **5.369**
- `E110` in `chennai_coastal` and `delhi_inland`: worst `corrosion` **59.150**, best `biomedical` **64.099**, swing **4.949**

This is another clear sign that the weighting system is a major driver of behavior.

### 9.5 Top-Ranked Alloys Across the Sweep

Highest mean composite scores across the application sweep:

- `3003`: **66.087**
- `Rene 41`: **65.977**
- `5083-H116`: **65.842**
- `6082-T6`: **65.842**
- `6061-T6`: **65.636**
- `1100`: **65.519**
- `2024-T3`: **65.108**
- `2014-T6`: **65.014**
- `Waspaloy`: **65.008**
- `301`: **64.770**

What stands out is that several aluminum alloys do extremely well across a wide spread of conditions. That suggests the current composite system rewards lightweight, broadly manufacturable, corrosion-friendly materials very strongly.

### 9.6 Most Variable Alloys

Alloys with the largest score variability:

- `Rene 41`: std **1.744**
- `Hastelloy C276`: std **1.702**
- `Waspaloy`: std **1.635**
- `2507`: std **1.618**
- `Nimonic 80A`: std **1.485**
- `IN625`: std **1.472**
- `Haynes 230`: std **1.462**
- `Haynes 188`: std **1.460**
- `IN718`: std **1.369**
- `2205`: std **1.341**

These are exactly the kinds of alloys I would expect to be highly context-sensitive: superalloys and advanced corrosion/high-temperature alloys show more application-dependent behavior.

### 9.7 No Alloy Was Perfect Across All 42 Domains

One very important observation:

- there were **no fail-free rows**

That means no alloy passed every domain without any failing domain checks.

This is not necessarily bad. It actually makes sense, because the engine covers very different objectives: corrosion, superconductivity, biocompatibility, catalysis, nuclear compatibility, manufacturing, and more. No single alloy should dominate every domain. The right interpretation is:

- AIDE is a **tradeoff evaluator**, not a perfect-alloy detector.

### 9.8 Pairwise Comparison Study

Closest or essentially tied alloy pairs:

- `15-5PH` vs `17-4PH`: exact tie, `42` domain ties, L1 distance `0.036`
- `321` vs `347`: exact tie, `42` domain ties, L1 distance `0.014`
- `4140` vs `4340`: exact tie, `42` domain ties, L1 distance `0.037`
- `5083-H116` vs `6082-T6`: exact tie, `42` domain ties, L1 distance `0.068`

These are very strong sanity-check results. Similar alloy families are being treated similarly.

Most separated pairs:

- `3003` vs `WE43`: delta **7.658**
- `5083-H116` vs `WE43`: delta **7.403**
- `6082-T6` vs `WE43`: delta **7.403**
- `6061-T6` vs `WE43`: delta **7.149**
- `3003` vs `H13`: delta **7.110**

Most frequent comparison winners:

- `3003` won **77** comparisons
- `5083-H116` won **75**
- `6082-T6` won **75**
- `6061-T6` won **74**
- `1100` won **73**

This reinforces the earlier observation that aluminum-family alloys are currently favored broadly.

### 9.9 Which Domains Really Discriminate

Highest average domain scores:

- `radiation_physics`: **95.299**
- `thermodynamics`: **89.228**
- `mechanical`: **88.750**
- `oxidation`: **85.087**
- `formability`: **82.404**
- `hume_rothery`: **81.987**

Lowest average domain scores:

- `shape_memory`: **20.000**
- `calphad_stability`: **20.000**
- `additive_manufacturing`: **27.746**
- `galvanic_compatibility`: **30.416**
- `transformation_kinetics`: **31.953**
- `impact_toughness`: **38.750**

Most variable domains:

- `biocompatibility`: std **32.291**
- `catalysis`: std **20.598**
- `oxidation`: std **19.461**
- `machinability`: std **18.506**
- `transformation_kinetics`: std **17.659**
- `weldability`: std **17.134**

Flat or near-flat domains:

- `mechanical`: std **0.000**
- `thermal_properties`: std **0.000**
- `acoustic_properties`: std **0.000**
- `shape_memory`: std **0.000**
- `calphad_stability`: std **0.000**
- `fracture_mechanics`: std **0.000**

This is one of the most useful findings from the whole study. It shows that:

- some domains are doing real discrimination,
- some domains are mostly constant over the current alloy set,
- and future refinement should focus on the low-variance domains if the goal is a more expressive composite score.

### 9.10 Domains Producing the Most Fails

Most fail-heavy domains:

- `galvanic_compatibility`: **73,800** fail checks
- `additive_manufacturing`: **49,200**
- `biocompatibility`: **34,500**
- `castability`: **27,300**
- `machinability`: **25,800**
- `solidification`: **20,100**
- `india_corrosion_index`: **19,320**

This tells me those domains are currently acting as strong filters, and probably deserve extra calibration attention if the intent is to avoid over-penalizing broad sections of the alloy library.

### 9.11 Intent Parser Observations

From the intent dataset:

- rows: **96**
- mode match rate: **80.21%**
- application match rate: **50.55%**
- classifier source: **all rule_based**

The reason the source is all `rule_based` is that the dataset generation was intentionally run in deterministic mode without local or remote intent LLM assistance.

Interpretation:

- the parser is already quite solid at detecting the broad workflow,
- but exact application naming still has room to improve,
- and the intent dataset is a good future benchmark for parser refinement.

---

## 10. Validation and Testing Notes

I also ran targeted tests to confirm that the codebase still works as a system and not only as static files.

### 10.1 Tests Run

Successful test command in the project virtual environment:

```powershell
.\.venv312\Scripts\python.exe -m unittest backend.tests.test_api tests.test_query_behaviors
```

Result:

- **10 tests passed**
- runtime about **11 seconds**

### 10.2 What Those Tests Cover

`backend/tests/test_api.py` verifies:

- root endpoint
- health endpoint
- domain listing
- unified engine run
- unified composition analysis
- error behavior on empty payload

`tests/test_query_behaviors.py` verifies:

- fusible query intent extraction
- electronics query intent extraction
- fusible pipeline family preference
- diversity among top candidates for electronics-style design prompts

### 10.3 Practical Runtime Observation

While testing, the local model stack reported memory pressure warnings from Ollama, but the tests still passed. That is a positive sign:

- the core system can still function even when the local LLM path is constrained,
- because the deterministic and heuristic layers remain usable.

---
## 11. Strengths, Weaknesses, and What I Learned

### 11.1 Strengths

- The project has a clear layered architecture.
- Physics scoring is modular and easy to extend.
- The system is not fully dependent on LLM availability.
- There is strong coverage of alloy evaluation domains.
- The dataset generator is excellent for large-scale validation.
- Similar alloy families usually remain close in comparisons, which is a good sign.

### 11.2 Weaknesses or Gaps

- Several domains appear flat over the current dataset and may need deeper formulas or calibration.
- Composite score spread is narrower than it could be.
- The repo contains mirrored or artifact code trees that can confuse maintenance.
- There are two UI surfaces, which is useful, but also increases maintenance complexity.
- Exact application classification is weaker than general mode routing.

### 11.3 What I Learned About the Project

The more I studied it, the clearer it became that AIDE v5 is strongest as a **decision-support engine for alloy tradeoffs**. It is not just trying to predict one property. It is trying to combine many weak and strong signals into a practical design recommendation.

That is why the project feels closer to an **expert-system-plus-search engine** than a single ML model.

---

## 12. Recommended Next Improvements

If I were continuing this project, these would be the most valuable next steps:

1. Improve low-variance domains so they contribute more real discrimination.
2. Use the generated intent dataset to systematically improve application classification.
3. Benchmark composite scores against a curated real-world ranking set for key applications.
4. Document which UI is the primary product surface: Streamlit, web frontend, or both.
5. Keep deployment mirrors and scratch artifacts clearly separated from core source code.
6. Add domain-wise calibration notes so users know which modules are strong heuristics versus light placeholders.

---

## 13. Final Conclusion

AIDE v5 is a serious and thoughtfully structured alloy design project. It already contains:

- a meaningful architecture,
- a broad evaluation framework,
- reusable APIs,
- multiple interfaces,
- a large knowledge base,
- and a strong foundation for future materials informatics work.

My overall conclusion is:

**AIDE v5 already works well as a multi-objective alloy recommendation and analysis platform, and the dataset experiments prove that it is stable, scalable, and internally coherent.**

The most special thing I observed is that the engine is currently driven most strongly by **design intent and weight priorities**, which means it is especially useful for guided alloy exploration. The next stage of improvement should focus on calibration depth, especially in the flatter physics domains and in finer-grained intent classification.

---

## 14. Useful Reproduction Commands

Start the backend:

```powershell
.\START_AIDE.ps1
```

Run the smoke tests:

```powershell
.\.venv312\Scripts\python.exe -m unittest backend.tests.test_api tests.test_query_behaviors
```

Generate the datasets again:

```powershell
.\.venv312\Scripts\python.exe generate_aide_datasets.py
```

<!-- DOMAIN_VARIATION_APPENDIX_START -->

## 15. Domain Variation Microdataset Addendum

I generated an additional RAM-safe variation pack around every catalog alloy so the report is no longer limited to only the base library compositions.

- Variation sweep rows: **32,760**
- Variation specs per alloy: **21** (1 base + 20 perturbations)
- Environments: **5**
- Processes: **4**
- Domain top-list files: **42** small CSVs under `C:\project 2\aide v5\dataset_exports\aide_domain_variation_pack\domain_toplists`
- Domain winner summary file: `C:\project 2\aide v5\dataset_exports\aide_domain_variation_pack\aide_domain_winners.csv`
- Most repeated domain-winning alloy families: Rene 41 (19), 5083-H116 (6), 316L (4), AM60B (2), C95400 (2)

For each domain I kept the top **50** candidates from the variation sweep, then reran the winning composition to extract concise reasons, likely uses, and faults.

### Domain-Wise Best Compositions

- **Acoustic Properties**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 64.0). Why: v_L = 5.95 km/s  [4,9]  ideal for ultrasonic non-destructive testing; recommend probe frequency  .... Use: vibration and acoustic damping exploration; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Additive Manufacturing**: Al 90.3%, Zn 5.5%, Mg 2.4%, Cu 1.5%, Cr 0.2%, Mn 0.1% (base alloy `7075-T6`, variant `perturb_s060_seed_89`, score 42.0). Why: High resistivity  good laser absorption at 1064nm. Use: powder-bed and AM process candidate screening; context: lightweight aluminium structure; family uses: M16 rifle receiver, aircraft wing spar. Faults: Wide freeze range (1487K)  high crack risk | High residual stress expected  substrate preheating needed.
- **Biocompatibility**: Ti 93.7%, Al 3.4%, V 2.9% (base alloy `Ti-3Al-2.5V`, variant `perturb_s060_seed_83`, score 100.0). Why: CytoIdx = 0.017 < 0.10  biocompatible; low ion release toxicity | Osseo = 0.94  excellent bone-implant bonding expected (Ti-rich alloy). Use: implant and body-contact screening; context: lightweight titanium alloy; family uses: bicycle frame, hydraulic tubing. Faults: CALPHAD Stability 20.0, Impact Toughness 20.0, Shape Memory 20.0.
- **CALPHAD Stability**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 20.0). Why: Install with: pip install pycalphad CALPHAD check skipped; empirical Miedema/Omega used in Domain 1.. Use: thermodynamic database compatibility and phase-map screening; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, Shape Memory 20.0.
- **Castability**: Mg 93.2%, Al 6.8% (base alloy `AM60B`, variant `perturb_s060_seed_83`, score 100.0). Why: Narrow (10K)  good castability | High fluidity (74.3)  mould filling OK. Use: casting routes and foundry processing; context: open-ended advanced alloy; family uses: instrument panel, seat frame. Faults: Galvanic Compatibility 9.2, CALPHAD Stability 20.0, Catalysis 20.0.
- **Catalysis**: Al 94.5%, Mg 4.2%, Mn 0.7%, Fe 0.4%, Cr 0.1%, Si 0.1% (base alloy `5083-H116`, variant `perturb_s040_seed_67`, score 100.0). Why: _d = -1.93 eV  near HER volcano peak (G_H  0; Pt: 2.3, Ni: 1.3 eV) | _d = -1.93 eV  near ORR volcano peak (Pt: 2.3 eV, Pd: 1.8 eV). Use: surface-reaction and catalytic screening; context: lightweight aluminium structure; family uses: LNG tank, cryogenic. Faults: CALPHAD Stability 20.0, Shape Memory 20.0, Transformation Kinetics 20.0.
- **Corrosion**: Fe 64.6%, Cr 24.5%, Ni 6.8%, Mo 3.8%, N 0.3% (base alloy `2507`, variant `perturb_s060_seed_89`, score 100.0). Why: PREN = 41.1  40  excellent pitting resistance (super-duplex class) | Cr = 24.5 wt%  10.5%  continuous Cr2O3 passive film forms. Use: marine, chloride, and chemical process service; context: chloride-resistant stainless alloy; family uses: deep water, flue gas desulfurisation. Faults: Biocompatibility 18.3, CALPHAD Stability 20.0, Shape Memory 20.0.
- **Creep**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 77.5). Why: T/Tm = 0.158 < 0.3  diffusion creep negligible | Ni = 51 wt%, Al+Ti = 5.1 wt%  Ni3(Al,Ti) ' precipitation strengthening expected. Use: elevated-temperature load-bearing service; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Diffusion**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 64.0). Why:  = 5.0%  similar atomic sizes  low Kirkendall void risk. Use: diffusion-sensitive joining, coating, and heat-treatment work; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Electronic Structure**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 64.0). Why: VEC = 8.20  metallic alloy (electrons in partially filled d/sp bands). Use: electronic-functional screening and conductivity-adjacent design; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Fatigue & Fracture**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 66.25). Why: SFE  0 mJ/m2 < 25  planar slip, low crack closure, excellent fatigue crack resistance. Use: cyclic loading and durability-driven components; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Formability**: Al 94.5%, Mg 4.2%, Mn 0.7%, Fe 0.4%, Cr 0.1%, Si 0.1% (base alloy `5083-H116`, variant `perturb_s040_seed_67`, score 100.0). Why: n0.29  good formability (deep drawing OK) | =0.342  metallic, ductile. Use: sheet, forming, and deformation-heavy manufacturing; context: lightweight aluminium structure; family uses: LNG tank, cryogenic. Faults: CALPHAD Stability 20.0, Shape Memory 20.0, Transformation Kinetics 20.0.
- **Fracture Mechanics**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 70.0). Why: B/G=2.03 > 1.75  ductile fracture expected. Use: crack-tolerant structures and damage-tolerant design; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Galvanic Compatibility**: Mo 27.0%, Nb 24.9%, W 24.5%, Ta 23.6% (base alloy `NbMoTaW`, variant `perturb_s060_seed_73`, score 53.33). Why: E=49mV  compatible. Use: multi-metal assemblies and galvanic exposure; context: refractory high-temperature alloy; family uses: HIP tooling, ultra high temperature. Faults: E=191mV  monitor, insulate if wet | E=199mV  monitor, insulate if wet.
- **Grain Boundary**: Cu 84.2%, Al 12.3%, Fe 3.5% (base alloy `C95400`, variant `perturb_s060_seed_83`, score 68.75). Why: Net GBE = 0.0000 at%  negligible GB embrittlement risk | Low Bi/Pb/Sn in Cu-base  LME risk negligible. Use: microstructural stability sensitive applications; context: high-conductivity copper alloy; family uses: marine propeller, pump impeller. Faults: Additive Manufacturing 0.0, CALPHAD Stability 20.0, Shape Memory 20.0.
- **Heat Treatment Response**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 100.0). Why: 7.8% age-hardenable elements  ageing HT viable | 6.6% refractory elements  grain growth inhibited. Use: quench, temper, aging, and precipitation-tuning workflows; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Hume-Rothery**: Ni 21.5%, Fe 20.8%, Mn 20.4%, Cr 19.9%, Co 17.5% (base alloy `CoCrFeMnNi`, variant `perturb_s060_seed_83`, score 100.0). Why:  = 1.13%  5%  good lattice compatibility |  = 0.139  acceptable; limited ordering tendency. Use: composition compatibility and phase-selection screening; context: high-entropy alloy; family uses: cryogenic structural, research benchmark. Faults: Biocompatibility 0.0, CALPHAD Stability 20.0, Impact Toughness 20.0.
- **Hydrogen Embrittlement**: Fe 64.6%, Cr 18.1%, Ni 13.9%, Mo 2.2%, Mn 1.2% (base alloy `316L`, variant `perturb_s060_seed_71`, score 77.5). Why: No significant hydride-forming elements  no -hydride risk | FCC austenite stable (Ni+Cr SS)  H diffusivity  1014 m2/s  high HE resistance. Use: hydrogen-rich, sour, or cathodic environments; context: chloride-resistant stainless alloy; family uses: coastal bridge, marine hardware. Faults: HEI = 0.260  moderate risk; avoid H2 atmosphere or cathodic charging environments.
- **Hydrogen Storage**: Mg 93.2%, Al 6.8% (base alloy `AM60B`, variant `perturb_s060_seed_83`, score 77.5). Why: H capacity  7.60 wt%  meets or exceeds DOE 2025 target (5.5 wt%). Use: hydrogen uptake and storage exploration; context: open-ended advanced alloy; family uses: instrument panel, seat frame. Faults: Galvanic Compatibility 9.2, CALPHAD Stability 20.0, Catalysis 20.0.
- **Impact Toughness**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 60.0). Why: FCC-dominant  no sharp ductile-brittle transition. Use: impact-loaded or low-temperature toughness service; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **India Corrosion Index**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 100.0). Why: ICI=42.8 >= 40  suitable for Indian coastal/tropical exposure. env=chennai_coastal, RH=75%, Cl=40... | pH=7.3  within passive film stability range (6.5-9.0).. Use: Indian climate corrosion screening and coastal exposure; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Machinability**: Al 94.5%, Mg 4.2%, Mn 0.7%, Fe 0.4%, Cr 0.1%, Si 0.1% (base alloy `5083-H116`, variant `perturb_s040_seed_67`, score 100.0). Why: MI=308% (vs AISI 1212=100%)  good | HV=17  easy cutting. Use: machined-part production and tool-life-sensitive work; context: lightweight aluminium structure; family uses: LNG tank, cryogenic. Faults: CALPHAD Stability 20.0, Shape Memory 20.0, Transformation Kinetics 20.0.
- **Magnetism**: W 25.4%, Nb 25.2%, Mo 25.0%, Ta 24.4% (base alloy `NbMoTaW`, variant `perturb_s020_seed_31`, score 70.0). Why: Ferro-formers = 0.0 at%  non-ferromagnetic (paramagnetic or diamagnetic). Use: magnetic-functional or electromagnetic hardware; context: refractory high-temperature alloy; family uses: HIP tooling, ultra high temperature. Faults: Additive Manufacturing 18.3, CALPHAD Stability 20.0, Shape Memory 20.0.
- **Mechanical**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 88.75). Why: B/G = 2.03  1.75  ductile regime |  = 0.289  0.26  ductile (metallic bonding). Use: load-bearing and ductility-biased structural service; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Nuclear Fuel Compatibility**: Zr 97.9%, Nb 1.0%, Sn 1.0%, Fe 0.1% (base alloy `ZIRLO`, variant `perturb_s040_seed_53`, score 77.5). Why: Zr = 98.1%  Zircaloy-type; low _thermal = 0.185 barns; excellent corrosion in water at 300400C. Use: reactor-core and fuel-adjacent compatibility screening; context: nuclear service alloy; family uses: PWR fuel cladding, advanced cladding. Faults: Galvanic Compatibility 18.3, CALPHAD Stability 20.0, Impact Toughness 20.0.
- **Optical Properties**: Cu 84.2%, Al 12.3%, Fe 3.5% (base alloy `C95400`, variant `perturb_s060_seed_83`, score 55.0). Why: E_p = p = 30.8 eV (Al: 15.8 eV, Cu: 10.8 eV, Ag: 3.8 eV experimental  Ashcroft & Mermin 1) | R  94% at 3 eV (Ag: 99%, Cu: 97%, Fe: 70%, Pt: 70%  Ziman 1960). Use: optical-functional and reflectivity-sensitive materials; context: high-conductivity copper alloy; family uses: marine propeller, pump impeller. Faults: Additive Manufacturing 0.0, CALPHAD Stability 20.0, Shape Memory 20.0.
- **Oxidation**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 100.0). Why: PBR = 1.89  [1.0, 2.5]  protective adherent oxide scale | Cr = 20.1 wt%  Cr2O3 protective scale (G1000K  450 kJ/mol O2). Use: hot oxidizing environments and scale-forming service; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Phase Stability**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 92.5). Why: -formers = 29.0%, VEC = 8.20  low TCP/ risk | No -phase risk (Ti+Zr=4%, -stab=29.0%). Use: phase-robust, heat-exposed alloy selection; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Plasticity**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 64.0). Why: 12 slip systems (FCC {111}<110>)  satisfies Von Mises 5 for polycrystal ductility. Use: forming-heavy or ductility-prioritized processing; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Radiation Physics**: Fe 64.6%, Cr 18.1%, Ni 13.9%, Mo 2.2%, Mn 1.2% (base alloy `316L`, variant `perturb_s060_seed_71`, score 100.0). Why:  = 3.046 barns  low neutron absorption; good structural material | No radioactive elements above 0.01 at%. Use: irradiation-facing and reactor-adjacent service; context: chloride-resistant stainless alloy; family uses: coastal bridge, marine hardware. Faults: Additive Manufacturing 18.3, Biocompatibility 18.3, CALPHAD Stability 20.0.
- **Regulatory & Safety**: Al 94.5%, Mg 4.2%, Mn 0.7%, Fe 0.4%, Cr 0.1%, Si 0.1% (base alloy `5083-H116`, variant `perturb_s040_seed_67`, score 91.0). Why: No restricted substances above RoHS thresholds | No IARC Group 1 or 2A carcinogens above 0.1 wt%. Use: restricted-material and safety-sensitive applications; context: lightweight aluminium structure; family uses: LNG tank, cryogenic. Faults: CALPHAD Stability 20.0, Shape Memory 20.0, Transformation Kinetics 20.0.
- **Relativistic Effects**: Al 94.5%, Mg 4.2%, Mn 0.7%, Fe 0.4%, Cr 0.1%, Si 0.1% (base alloy `5083-H116`, variant `perturb_s040_seed_67`, score 77.5). Why: f_rel = 0.909%  negligible relativistic effects (all Z < 70). Use: heavy-element electronic behavior exploration; context: lightweight aluminium structure; family uses: LNG tank, cryogenic. Faults: CALPHAD Stability 20.0, Shape Memory 20.0, Transformation Kinetics 20.0.
- **Shape Memory**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 20.0). Why: No classical SMA composition detected (NiTi: Ni50+Ti50; Cu-Zn-Al; Fe-Mn-Si). Use: actuation and recoverable-strain exploration; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Solidification**: Al 94.5%, Mg 4.2%, Mn 0.7%, Fe 0.4%, Cr 0.1%, Si 0.1% (base alloy `5083-H116`, variant `perturb_s040_seed_67`, score 85.0). Why: Narrow freeze range (10K)  low segregation | High thermal conductivity  planar/cellular preferred. Use: freezing-path and segregation-sensitive processing; context: lightweight aluminium structure; family uses: LNG tank, cryogenic. Faults: CALPHAD Stability 20.0, Shape Memory 20.0, Transformation Kinetics 20.0.
- **Structural Efficiency**: Ti 76.7%, Mo 16.6%, Al 3.4%, Nb 3.1%, Si 0.2% (base alloy `Beta-21S`, variant `perturb_s060_seed_83`, score 83.12). Why: M1 = 2.34  above steel (1.69); good lightweight stiffness | M2 = 9.7  comparable to structural steel (~7.2). Use: strength-to-weight and lightweight load-bearing service; context: lightweight titanium alloy; family uses: aerospace fastener, exhaust nozzle. Faults: CALPHAD Stability 20.0, Impact Toughness 20.0, Shape Memory 20.0.
- **Superconductivity**: Ti 20.7%, Zr 20.1%, Nb 20.0%, V 19.8%, Mo 19.4% (base alloy `TiZrNbMoV`, variant `perturb_s060_seed_89`, score 85.0). Why: Tc  12.7 K  promising conventional superconductor | VEC = 4.69  5  Matthias peak (Nb, V compounds, A15 phases). Use: cryogenic and superconducting exploration; context: high-entropy alloy; family uses: high temperature structural. Faults: Additive Manufacturing 18.3, CALPHAD Stability 20.0, Shape Memory 20.0.
- **Surface Energy**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 66.25). Why:  = 2.20 J/m2 > 1.5  high-energy metallic surface; wetted by water, adhesives. Use: surface-controlled processing and interface behavior; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Thermal Properties**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 55.0). Why: _e = L0T/ = 77.7 W/(mK) at 298 K (electronic contribution) |  = 98.3 W/(mK) (rule of mixtures from tabulated values). Use: heat-flow and thermal-management service; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Thermodynamics**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 100.0). Why: Hmix = -10.13 kJ/mol  [-15,+5]  solid-solution favoured | Smix = 11.60  11 J/molK  high-entropy regime. Use: solid-solution and general alloy stability screening; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: Biocompatibility 0.0, Additive Manufacturing 18.3, CALPHAD Stability 20.0.
- **Transformation Kinetics**: Fe 64.6%, Cr 18.1%, Ni 13.9%, Mo 2.2%, Mn 1.2% (base alloy `316L`, variant `perturb_s060_seed_71`, score 73.33). Why: Ms = 21 degC  martensite forms partially or not at room T. Austenite likely retained. Check Md30 ... | Operating T (25 degC) outside sigma-formation window (600-950 degC). Sigma kinetics negligible.. Use: heat-treatment path design and transformation control; context: chloride-resistant stainless alloy; family uses: coastal bridge, marine hardware. Faults: Additive Manufacturing 18.3, Biocompatibility 18.3, CALPHAD Stability 20.0.
- **Tribology & Wear**: Ni 51.2%, Cr 20.1%, Co 12.2%, Mo 10.9%, Ti 3.4%, Al 1.7% (base alloy `Rene 41`, variant `perturb_s060_seed_83`, score 66.25). Why: Good galling resistance (Cr=20.1%, Mo=10.9%, H=837 MPa). Use: sliding, contact, and wear-limited service; context: turbine-grade superalloy; family uses: afterburner, exhaust nozzle. Faults: H/E = 0.0038  soft alloy; higher wear rate (Pb, Al soft alloys ~0.003).
- **Weldability**: Fe 64.6%, Cr 18.1%, Ni 13.9%, Mo 2.2%, Mn 1.2% (base alloy `316L`, variant `perturb_s060_seed_71`, score 100.0). Why: Cr_eq=20.3, Ni_eq=14.5  Austenite dominant  good weldability | Nb+V+Ti = 0.000 wt%  low reheat cracking risk. Use: fabrication-heavy structures and welded assemblies; context: chloride-resistant stainless alloy; family uses: coastal bridge, marine hardware. Faults: Additive Manufacturing 18.3, Biocompatibility 18.3, CALPHAD Stability 20.0.

<!-- DOMAIN_VARIATION_APPENDIX_END -->
