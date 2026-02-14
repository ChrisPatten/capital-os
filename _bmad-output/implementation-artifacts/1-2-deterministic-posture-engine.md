# Story 1.2: Deterministic Posture Engine

Status: done

## Story

As a family-office AI operator,
I want a deterministic posture computation engine,
so that posture metrics are reproducible and safe for automated decisioning.

## Acceptance Criteria

1. Posture engine computes all FR-06 metrics:
  - `fixed_burn`
  - `variable_burn`
  - `volatility_buffer`
  - `reserve_target`
  - `liquidity`
  - `liquidity_surplus`
  - `reserve_ratio`
  - `risk_band`
2. Numeric outputs are normalized to 4 decimal places using round-half-even where applicable.
3. Output ordering and serialization are deterministic (same state/config -> same `output_hash`).
4. Risk-band derivation is explicit and deterministic from computed inputs.
5. Unit tests cover formula correctness and boundary conditions.
6. Replay tests confirm stable `output_hash` for repeated runs on identical state.

## Tasks / Subtasks

- [x] Task 1: Implement posture computation service (AC: 1, 2, 4)
  - [x] Add `src/capital_os/domain/posture/engine.py` for deterministic metric computation
  - [x] Keep formulas explicit and independently testable
  - [x] Ensure clear handling of zero/near-zero denominator cases
- [x] Task 2: Enforce deterministic output shaping (AC: 2, 3)
  - [x] Normalize decimals and ordering before hashing/output
  - [x] Reuse existing canonical hashing utilities where possible
- [x] Task 3: Add unit test coverage for formulas (AC: 5)
  - [x] Create `tests/unit/test_posture_engine.py`
  - [x] Cover normal cases, boundaries, and invalid input handling
- [x] Task 4: Add replay determinism checks (AC: 6)
  - [x] Extend `tests/replay/test_output_replay.py` for posture engine outputs
  - [x] Verify repeated runs produce identical hash for seeded state

## Dev Notes

### Developer Context Section

- This story depends on Story 1.1 posture input model and selection output.
- Scope is domain computation only; tool contract wiring is Story 1.3.
- Avoid introducing side effects or DB mutations in computation logic.

### Technical Requirements

- Determinism is the primary quality gate.
- All formula behavior must be transparent and auditable.
- Use Decimal-safe arithmetic patterns consistent with ledger invariants.

### Architecture Compliance

- Keep layering strict:
  - posture engine in domain layer
  - no API concerns in this story
- Preserve canonical SQLite-as-truth and replayability patterns.

### Library and Framework Requirements

- Use current repository dependencies from `pyproject.toml`.
- No new libraries for math/analytics unless absolutely required.

### File Structure Requirements

- Add/modify within:
  - `src/capital_os/domain/posture/`
  - `tests/unit/`
  - `tests/replay/`
- Do not alter existing tool modules in this story except minimal integration stubs if required by tests.

### Testing Requirements

- Unit tests for every metric formula and branching rule.
- Determinism tests on ordering + hashing input shape.
- Full regression suite remains green.

### Previous Story Intelligence

- Story 1.1 established input model and deterministic account-selection guardrails.
- Reuse that contract directly to avoid duplicate selection logic.

### References

- [Source: `initial_prd.md`]
- [Source: `ARCHITECTURE.md`]
- [Source: `_bmad-output/planning-artifacts/epic-1-capital-posture.md`]
- [Source: `_bmad-output/implementation-artifacts/1-1-posture-domain-model-and-inputs.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Create-story workflow executed in YOLO mode per SM activation rule.
- `pytest -q tests/unit/test_posture_engine.py tests/replay/test_output_replay.py`
- `pytest -q`
- `pytest -q tests/unit/test_posture_engine.py tests/replay/test_output_replay.py`
- `pytest -q`

### Implementation Plan

- Add a deterministic posture engine model with explicit FR-06 formulas and risk-band thresholding.
- Normalize all numeric outputs to `NUMERIC(20,4)` semantics using existing round-half-even normalization helper.
- Produce hash-stable output via canonical payload hashing.
- Add dedicated unit tests for formula correctness/boundaries and replay tests for stable output hash.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented `PostureComputationInputs` and `PostureMetrics` in a new domain posture engine.
- Added explicit FR-06 formula computation for reserve target, liquidity surplus, reserve ratio, and deterministic risk band.
- Added zero-denominator handling for reserve ratio to avoid division instability.
- Added deterministic output helper returning `output_hash` derived from canonical serialization.
- Added posture engine unit tests covering normal calculations, round-half-even normalization, ratio boundaries, and zero reserve target handling.
- Extended replay suite with repeated-run hash reproducibility assertions for posture engine output.
- Full regression suite passed (`34 passed`).
- Senior review auto-fix pass applied: deterministic serialized output payload enforced for `compute_posture_metrics_with_hash`.
- Senior review auto-fix pass applied: added invalid-input tests, risk-threshold boundary tests, and near-zero reserve-target determinism tests.
- Full regression suite passed after review fixes (`40 passed`).

### File List

- `_bmad-output/implementation-artifacts/1-2-deterministic-posture-engine.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/capital_os/domain/posture/__init__.py`
- `src/capital_os/domain/posture/engine.py`
- `tests/replay/test_output_replay.py`
- `tests/unit/test_posture_engine.py`

## Change Log

- 2026-02-14: Implemented deterministic posture engine formulas and risk-band derivation with explicit zero-denominator behavior.
- 2026-02-14: Added posture engine unit tests plus replay hash determinism checks and validated full test suite.
- 2026-02-14: Senior code review fixes applied for deterministic output serialization and expanded formula/input boundary test coverage.

## Senior Developer Review (AI)

### Review Date

2026-02-14

### Reviewer

GPT-5 Codex (Senior Developer Review Workflow)

### Outcome

Approve

### Findings and Resolution

- [x] [HIGH] Added invalid input coverage for negative burn/reserve values (`tests/unit/test_posture_engine.py`).
- [x] [HIGH] Enforced deterministic serialized output shape in `compute_posture_metrics_with_hash` (`src/capital_os/domain/posture/engine.py`).
- [x] [MEDIUM] Added risk-band threshold edge tests for `0.5000` and `1.0000` (`tests/unit/test_posture_engine.py`).
- [x] [MEDIUM] Added near-zero reserve-target determinism tests (`tests/unit/test_posture_engine.py`).
