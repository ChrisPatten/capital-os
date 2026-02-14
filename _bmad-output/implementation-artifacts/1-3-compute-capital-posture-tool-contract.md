# Story 1.3: Compute Capital Posture Tool Contract

Status: done

## Story

As a family-office AI operator,
I want a schema-validated `compute_capital_posture` tool,
so that posture outputs are consistently available via the Capital OS tool API with full observability.

## Acceptance Criteria

1. `compute_capital_posture` request/response schemas are defined and validated.
2. Tool is wired into `POST /tools/{tool_name}` routing and resolves to the posture domain service.
3. Validation failures return deterministic 422 error payload shape and are always logged.
4. Successful responses include deterministic `output_hash`.
5. Event logs for both success and failure include required fields (`tool_name`, `correlation_id`, `input_hash`, `output_hash`, `timestamp`, `duration`).
6. Existing tool behavior is not regressed.

## Tasks / Subtasks

- [x] Task 1: Add schema contract (AC: 1, 3, 4)
  - [x] Extend `src/capital_os/schemas/tools.py` with posture request/response models
  - [x] Ensure defaults and field constraints are explicit and deterministic
- [x] Task 2: Add tool handler (AC: 2, 4)
  - [x] Create `src/capital_os/tools/compute_capital_posture.py`
  - [x] Validate payload and delegate to posture domain service
- [x] Task 3: Wire API route mapping (AC: 2, 3, 5)
  - [x] Update `src/capital_os/api/app.py` `TOOL_HANDLERS`
  - [x] Ensure existing validation/error logging behavior applies unchanged
- [x] Task 4: Add integration and validation tests (AC: 3, 5, 6)
  - [x] Add/extend `tests/integration/test_tool_contract_validation.py`
  - [x] Add/extend `tests/integration/test_event_log_coverage.py`
  - [x] Add posture tool happy-path integration check

## Dev Notes

### Developer Context Section

- This story is transport/contract integration over Story 1.1 + 1.2 domain work.
- Keep the API layer thin and follow existing `record_*` tool patterns.
- Any output nondeterminism introduced here will break replay requirements.

### Technical Requirements

- Correlation IDs must remain traceable end-to-end.
- Error shapes should be deterministic and machine-readable.
- Do not bypass existing event logging pathways.

### Architecture Compliance

- Preserve existing boundary:
  - API/tool validation and mapping only
  - domain service owns computation behavior
- Maintain fail-closed behavior on write tools; this tool is read/compute but still must log success/failure.

### Library and Framework Requirements

- Continue using FastAPI + Pydantic v2 patterns currently in repo.
- Avoid ad-hoc serialization logic; rely on schema model dumping with deterministic ordering support where needed.

### File Structure Requirements

- Add/modify:
  - `src/capital_os/tools/compute_capital_posture.py`
  - `src/capital_os/schemas/tools.py`
  - `src/capital_os/api/app.py`
  - relevant tests under `tests/integration/`

### Testing Requirements

- Validation error shape tests for missing/invalid fields.
- Event logging assertions for both success/failure path.
- Regression test to confirm existing tools still pass.

### Previous Story Intelligence

- Story 1.1/1.2 output shape must be treated as source-of-truth for this contract.
- Avoid re-implementing posture formulas in tool layer.

### References

- [Source: `initial_prd.md`]
- [Source: `ARCHITECTURE.md`]
- [Source: `src/capital_os/api/app.py`]
- [Source: `_bmad-output/planning-artifacts/epic-1-capital-posture.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Create-story workflow executed in YOLO mode per SM activation rule.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/1-3-compute-capital-posture-tool-contract.md`
