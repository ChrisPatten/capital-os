# Story 7.2: Truth Selection Policy Wiring

Status: done

## Story

As a platform operator,  
I want configurable `balance_source_policy` wiring,  
so that read/reconciliation behavior can deterministically honor policy defaults.

## Acceptance Criteria

1. Add configurable balance source policy (`ledger_only|snapshot_only|best_available`) in runtime settings.
2. `get_account_balances` supports policy defaulting from config when not provided by caller.
3. Reconciliation method choices align with the same policy set.
4. Validation and behavior remain deterministic.

## Tasks / Subtasks

- [x] Task 1: Add runtime config policy (AC: 1)
  - [x] Extend `src/capital_os/config.py` with `balance_source_policy`.
  - [x] Enforce strict allowed values.
- [x] Task 2: Wire query service/tool default behavior (AC: 2, 4)
  - [x] Make `source_policy` optional in `GetAccountBalancesIn`.
  - [x] Resolve effective policy in `src/capital_os/domain/query/service.py`.
- [x] Task 3: Add deterministic tests (AC: 2, 4)
  - [x] Add default-policy integration test in `tests/integration/test_read_query_tools.py`.
  - [x] Adjust validation tests in `tests/integration/test_tool_contract_validation.py`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Added `CAPITAL_OS_BALANCE_SOURCE_POLICY` setting with strict normalization and validation.
- Updated read query behavior to apply configured policy when `source_policy` is omitted.
- Maintained deterministic output shape and explicit `source_policy` in tool response.

### File List

- `_bmad-output/implementation-artifacts/7-2-truth-selection-policy-wiring.md`
- `src/capital_os/config.py`
- `src/capital_os/domain/query/service.py`
- `src/capital_os/schemas/tools.py`
- `tests/integration/test_read_query_tools.py`
- `tests/integration/test_tool_contract_validation.py`
