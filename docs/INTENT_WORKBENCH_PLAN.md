# Intent Workbench Plan

## Goal
Give users a visible, editable bridge between natural-language input and the physics/ML engine so they can catch bad interpretation before a run starts.

## Why This Helps

Today the biggest trust break happens here:

1. User writes a plain-English request.
2. The app silently infers application, properties, constraints, and family rules.
3. Physics and ranking run on those hidden assumptions.
4. User only discovers the mismatch after seeing unrealistic candidates.

The Intent Workbench makes that hidden layer visible and editable.

## Core User Flow

1. User enters a query.
2. App parses intent but pauses on a review screen before running.
3. User sees:
   - inferred application family
   - target properties
   - density / cost / temperature constraints
   - required and excluded elements
   - active structural penalties and family rules
4. User can lock, edit, or remove any inferred item.
5. The engine runs using the reviewed intent, not just the raw text.
6. Results page shows which intent edits materially changed the candidate pool.

## UI Modules

- Intent Summary Card: plain-language summary of what the engine thinks the user wants
- Constraint Chips: editable chips for density, cost, environment, temperature, family locks
- Element Policy Panel: `must_include`, `exclude_elements`, and family caps
- Score Drivers Panel: which ranking and rejection rules are active for this run
- Diff Preview: compare `raw parsed intent` vs `user-reviewed intent`

## Backend / API Changes

- Add a normalized `intent_review` payload to `POST /api/v1/run`
- Preserve both `original_intent` and `resolved_intent` in results
- Return active rule groups:
  - family guidance
  - mechanism checks
  - structural chemistry caps
  - density/cost penalties
- Add a lightweight `intent_explain` block so frontend can describe why each rule was applied

## Success Criteria

- Fewer obviously wrong first-run candidates
- Fewer silent application-family mismatches
- Better interviewer/demo story because the app explains how it interpreted the request
- Easier debugging when outputs look off

## Delivery Phases

### Phase 1
- Read-only parsed intent preview
- Active rule summary
- Result payload includes resolved intent

### Phase 2
- Editable constraint chips
- User lock/unlock support
- Re-run with reviewed intent

### Phase 3
- Compare raw vs reviewed intent
- Show how candidate ranking changed after edits
- Save common intent templates for repeated use cases

## Demo Value

This feature turns AIDE from a black-box generator into a guided engineering assistant. It gives users a reason to trust the system because they can inspect and correct the interpretation before physics and ranking spend time on the wrong problem.
