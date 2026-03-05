# Story 17.2: Proposal Contract and Approval Decision Expansion

Status: done

## Story

As a family-office AI operator,  
I want duplicate-risk proposals to return complete side-by-side transaction context,  
so that approval decisions are informed, auditable, and consistent with existing proposal/approval behavior.

## Acceptance Criteria

1. Duplicate-risk-triggered `record_transaction_bundle` proposal response includes:
  - `proposed_transaction`
  - `matched_transactions[]` (all candidates)
  - `match_reason: "same_account_date_amount"`
2. Response payload shape is schema-validated and deterministic for identical state + input.
3. Existing proposal status contract is preserved (`status="proposed"`, no immediate commit).
4. Existing approval decision flow is preserved:
  - one decision per proposed transaction
  - `approve_proposed_transaction` commits exactly once
  - `reject_proposed_transaction` remains non-mutating
5. Duplicate-risk proposal payload is persisted for canonical replay and stable `output_hash`.
6. Approval response behavior remains backward-compatible for existing clients that rely on current committed/proposed fields.
7. Event logs capture proposal and decision paths with deterministic `input_hash`/`output_hash` and correlation IDs.

## Tasks / Subtasks

- [x] Task 1: Extend response schemas for duplicate-risk context (AC: 1, 2, 6)
  - [x] Update `RecordTransactionBundleOut` in `src/capital_os/schemas/tools.py` with optional duplicate-risk proposal fields.
  - [x] Define strict nested models for `proposed_transaction` and `matched_transactions[]`.
  - [x] Ensure unknown keys are rejected and canonical serialization is preserved.
- [x] Task 2: Expand proposal payload construction/persistence (AC: 1, 2, 3, 5)
  - [x] Update proposal response builder in `src/capital_os/domain/ledger/service.py` to include duplicate-risk context when triggered.
  - [x] Persist expanded response payload via existing proposal persistence path.
  - [x] Ensure deterministic ordering of matched transaction list.
- [x] Task 3: Preserve approval service semantics (AC: 4, 6)
  - [x] Verify `approve_proposed_transaction` and `reject_proposed_transaction` remain unchanged in decision semantics.
  - [x] Ensure proposal replay after commit/reject remains canonical and deterministic.
- [x] Task 4: Add integration/replay coverage for contract behavior (AC: 1–7)
  - [x] Integration: proposal response includes full duplicate-risk context fields.
  - [x] Integration: approve commits once; repeat approvals replay canonical result.
  - [x] Integration: reject remains non-mutating and idempotent.
  - [x] Replay: duplicate-risk proposal payload and output hash are reproducible.
  - [x] Contract validation: response shape stays backward-compatible for existing clients.

## Dev Notes

### Product Decisions Locked for This Story

- Duplicate-risk match criteria are exact (`account_id + effective_date + amount` normalized to 4dp).
- All candidate matches are returned for a single proposed transaction.
- Approval authority remains any writer.
- No global write lock is introduced; proposals are per transaction.

### Contract Strategy

- Add fields as optional extensions to avoid breaking existing consumers.
- Keep top-level status semantics unchanged (`committed`, `idempotent-replay`, `proposed`, `rejected`).
- Keep deterministic hashing over canonicalized response payloads.

### Suggested File Touchpoints

- `src/capital_os/schemas/tools.py`
- `src/capital_os/domain/ledger/service.py`
- `src/capital_os/domain/approval/service.py` (verification only; modify only if required)
- `tests/integration/test_approval_workflow.py`
- `tests/integration/test_tool_contract_validation.py`
- `tests/replay/test_output_replay.py`

### References

- [Source: `_bmad-output/planning-artifacts/epic-17-duplicate-risk-approval-gate.md`]
- [Source: `_bmad-output/implementation-artifacts/17-1-duplicate-risk-detection-rule-in-write-path.md`]
- [Source: `_bmad-output/planning-artifacts/epic-4-approval-gates.md`]
- [Source: `CONSTITUTION.md`]

## Dev Agent Record

### Implementation Plan

- Extend `RecordTransactionBundleOut` with strict nested models for duplicate-risk proposal context while keeping existing response fields optional/backward-compatible.
- Build deterministic duplicate-risk response context in ledger service and persist canonical proposal response payload for replay hash stability.
- Verify approval/rejection semantics remain unchanged; add and run integration/replay coverage for contract and determinism behavior.

### Debug Log

- Added strict nested models in `src/capital_os/schemas/tools.py` for `proposed_transaction` and `matched_transactions` with `extra="forbid"`.
- Added `_duplicate_risk_context` normalization path in `src/capital_os/domain/ledger/service.py` and used it during duplicate-risk proposal construction/persistence.
- Ensured deterministic ordering of matched transactions and normalized posting amounts/timestamps in proposal payload.
- Verified `approve_proposed_transaction` and `reject_proposed_transaction` behavior through existing + expanded integration/replay tests.
- Ran targeted suites:
- `pytest -q tests/integration/test_approval_workflow.py tests/replay/test_output_replay.py tests/integration/test_event_log_coverage.py tests/integration/test_tool_contract_validation.py`
- Added explicit success-path contract tests for backward-compatible committed/proposed response shapes and optional duplicate-risk extensions.
- Added explicit persistence assertions verifying canonical stored proposal payload normalizes to the API response contract with stable `output_hash`.

### Completion Notes

- ✅ AC1/AC2: Duplicate-risk proposal includes `proposed_transaction`, `matched_transactions[]`, and `match_reason` with strict schema validation.
- ✅ AC3/AC5: Proposal status contract remains `proposed` and expanded payload is persisted/replayed canonically with stable `output_hash`.
- ✅ AC4/AC6: Approval decision semantics remain one-decision canonical commit for approve, non-mutating idempotent reject, and backward-compatible response fields.
- ✅ AC7: Proposal + decision paths continue emitting deterministic event logs with correlation IDs and hash fields.
- ✅ Review remediation: Added direct contract-validation coverage for success-path backward compatibility and explicit duplicate-risk payload persistence checks.

### File List

- src/capital_os/schemas/tools.py
- src/capital_os/domain/ledger/service.py
- tests/integration/test_approval_workflow.py
- tests/integration/test_event_log_coverage.py
- tests/integration/test_tool_contract_validation.py
- _bmad-output/implementation-artifacts/17-2-proposal-contract-and-approval-decision-expansion.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

### Change Log

- 2026-03-05: Completed proposal-contract expansion for duplicate-risk flows, verified approval decision compatibility, and added deterministic replay/integration coverage updates.
- 2026-03-05: Senior review fixes applied: explicit backward-compat success contract assertions, explicit persisted-payload contract normalization checks, and story traceability corrections.

### Senior Developer Review (AI)

- Outcome: Changes Requested (addressed in this pass)
- Fixed High findings:
  - Added explicit success-path backward-compatible contract validation for `record_transaction_bundle` committed/proposed responses.
  - Corrected story File List to remove unmodified replay file and include actually changed validation/event-log coverage files.
- Fixed Medium findings:
  - Corrected Debug Log statement about idempotent replay context path.
  - Added explicit persisted `approval_proposals.response_payload` normalization checks against API response contract and `output_hash`.
  - Updated traceability notes to reflect current change set and executed verification.
