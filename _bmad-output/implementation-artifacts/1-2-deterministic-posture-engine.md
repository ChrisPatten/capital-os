# Story 1.2: Deterministic Posture Engine

Status: ready-for-dev

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

- [ ] Task 1: Implement posture computation service (AC: 1, 2, 4)
  - [ ] Add `src/capital_os/domain/posture/engine.py` for deterministic metric computation
  - [ ] Keep formulas explicit and independently testable
  - [ ] Ensure clear handling of zero/near-zero denominator cases
- [ ] Task 2: Enforce deterministic output shaping (AC: 2, 3)
  - [ ] Normalize decimals and ordering before hashing/output
  - [ ] Reuse existing canonical hashing utilities where possible
- [ ] Task 3: Add unit test coverage for formulas (AC: 5)
  - [ ] Create `tests/unit/test_posture_engine.py`
  - [ ] Cover normal cases, boundaries, and invalid input handling
- [ ] Task 4: Add replay determinism checks (AC: 6)
  - [ ] Extend `tests/replay/test_output_replay.py` for posture engine outputs
  - [ ] Verify repeated runs produce identical hash for seeded state

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

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/1-2-deterministic-posture-engine.md`
