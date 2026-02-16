# Story 10.2: Tool-Level Authorization and Correlation Integrity

Status: done

## Story

As a governance owner,
I want capability-based authorization enforced per tool and mandatory correlation IDs,
so that only permitted actors can execute sensitive actions and all requests are traceable end-to-end.

## Acceptance Criteria

1. Each tool invocation enforces capability checks and returns deterministic `403` when actor lacks permission.
2. `correlation_id` is mandatory for all tool invocations; missing/invalid values return deterministic `422` validation failures.
3. Successful and failed authorization decisions are event-logged with explicit authorization outcome metadata.
4. Authorization and correlation validation are deterministic and replay-stable for identical state + input.
5. Write-tool behavior remains fail-closed when event logging fails under authorized flows.

## Tasks / Subtasks

- [ ] Task 1: Define authorization model and capability map for existing tools (AC: 1, 3)
  - [ ] Add canonical tool-to-capability mapping and deterministic default-deny behavior.
  - [ ] Ensure support for read-only vs write permission boundaries.
- [ ] Task 2: Enforce per-tool authorization in dispatch path (AC: 1, 4)
  - [ ] Evaluate actor capability before handler execution.
  - [ ] Return deterministic `403` response envelope for denied calls.
- [ ] Task 3: Make `correlation_id` universally required and validated (AC: 2, 4)
  - [ ] Enforce schema requirement consistently across all tool request models.
  - [ ] Validate canonical format and deterministic failure payloads.
- [ ] Task 4: Extend logging and tests for authz/correlation outcomes (AC: 3, 5)
  - [ ] Capture authorization decision metadata in event records.
  - [ ] Add integration/replay coverage for deny/allow and correlation validation paths.

## Notes

### File Touchpoints / Implementation Notes

- Authorization policy and evaluation logic:
  - `src/capital_os/domain/policy/service.py`
  - `src/capital_os/domain/approval/policy.py`
- API dispatch and tool invocation gate:
  - `src/capital_os/api/app.py`
  - `src/capital_os/tools/__init__.py`
- Tool schemas (`correlation_id` required consistency):
  - `src/capital_os/schemas/tools.py`
- Event logging and deterministic hash inputs:
  - `src/capital_os/observability/event_log.py`
  - `src/capital_os/observability/hashing.py`
- Potential capability persistence/config support:
  - `src/capital_os/config.py`
  - `migrations/0008_api_security_runtime_controls.sql` (shared with 10.1/10.3 if needed)
- Tests:
  - `tests/integration/test_tool_contract_validation.py`
  - `tests/integration/test_event_log_coverage.py`
  - `tests/replay/test_output_replay.py`

- Authorization checks must execute before any ledger mutation path.
- Maintain deterministic ordering/representation of authorization metadata in logged payloads.
