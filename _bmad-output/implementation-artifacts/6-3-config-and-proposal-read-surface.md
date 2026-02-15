# Story 6.3: Config and Proposal Read Surface

Status: done

## Story

As a family-office AI operator,
I want deterministic proposal/config read tools and config-governance entry points,
so that I can inspect governance state and drive controlled config changes through auditable hooks.

## Acceptance Criteria

1. Implement read tools:
  - `list_proposals(limit?, cursor?, status?)`
  - `get_proposal(proposal_id)`
  - `get_config()`
2. Implement governance hooks:
  - `propose_config_change`
  - `approve_config_change`
3. Responses use deterministic ordering with explicit tie-break keys.
4. Validation failures return deterministic 422 payload shape and are event-logged.
5. Successful invocations emit event logs with required fields.
6. Read tools do not mutate canonical ledger tables.
7. Replay tests prove stable `output_hash` for identical state + input.

## Tasks / Subtasks

- [x] Task 1: Add schema/contracts for proposals/config tools and approval entry points (AC: 1, 2, 4)
- [x] Task 2: Extend query/repository logic for deterministic proposal listing and details reads (AC: 1, 3)
- [x] Task 3: Implement tool handlers and API wiring (AC: 1, 2, 5)
- [x] Task 4: Add integration/replay coverage (AC: 6, 7)

## Completion Notes

- Added deterministic proposal pagination ordered by `(created_at DESC, proposal_id ASC)`.
- Added proposal detail read including decision timeline ordering `(created_at ASC, decision_id ASC)`.
- Added `get_config` runtime/policy read view and auditable config change approval hooks via proposal records.
- Added validation and event-log coverage for query surface expansion.

## File List

- `_bmad-output/implementation-artifacts/6-3-config-and-proposal-read-surface.md`
- `src/capital_os/api/app.py`
- `src/capital_os/domain/ledger/repository.py`
- `src/capital_os/domain/query/pagination.py`
- `src/capital_os/domain/query/service.py`
- `src/capital_os/schemas/tools.py`
- `src/capital_os/tools/list_proposals.py`
- `src/capital_os/tools/get_proposal.py`
- `src/capital_os/tools/get_config.py`
- `src/capital_os/tools/propose_config_change.py`
- `src/capital_os/tools/approve_config_change.py`
- `tests/integration/test_epic6_query_surface_tools.py`
- `tests/replay/test_query_surface_replay.py`
- `tests/integration/test_tool_contract_validation.py`
- `tests/integration/test_event_log_coverage.py`
