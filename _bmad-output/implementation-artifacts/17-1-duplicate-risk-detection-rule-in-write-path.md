# Story 17.1: Duplicate-Risk Detection Rule in Write Path

Status: done

## Story

As a family-office AI operator,  
I want transaction writes to detect exact duplicate-risk matches before commit,  
so that accidental duplicate entries are routed through the existing proposal/approval workflow instead of silently committing.

## Acceptance Criteria

1. `record_transaction_bundle` evaluates duplicate-risk matches for all transaction writes before commit.
2. Duplicate-risk match criteria are exact and deterministic: `account_id`, `effective_date` (exact date), and normalized `amount` (`NUMERIC(20,4)`, round-half-even).
3. When at least one match exists, write returns `status="proposed"` and no ledger mutation occurs in that call.
4. Proposal response includes both sides:
  - proposed transaction details
  - all matched prior transaction candidates
5. Existing behavior is preserved for non-matching writes (commit path unchanged) and for `(source_system, external_id)` idempotent replay behavior.
6. Existing proposal semantics are preserved: one approval decision per proposed transaction, with no global write lock.
7. Duplicate-risk detection output ordering is deterministic across identical DB state and input.
8. Duplicate-risk-triggered proposal path is event-logged with required observability fields and deterministic `output_hash`.

## Tasks / Subtasks

- [x] Task 1: Add deterministic duplicate-risk query logic in ledger domain (AC: 1, 2, 7)
  - [x] Add repository/service logic to identify candidate matches by exact `effective_date`, `account_id`, and normalized amount.
  - [x] Ensure matching handles all postings in bundle and returns stable, deterministic ordering.
  - [x] Exclude the in-flight payload itself and maintain deterministic behavior under retry.
- [x] Task 2: Integrate duplicate-risk gate into write flow (AC: 1, 3, 5, 6)
  - [x] In `record_transaction_bundle`, evaluate duplicate-risk before direct commit.
  - [x] If candidates exist, route to existing proposal path (`status="proposed"`) without ledger mutation.
  - [x] Preserve current threshold/policy-driven approval behavior and external-id idempotency semantics.
- [x] Task 3: Expand proposal response payload for duplicate-risk context (AC: 4, 7)
  - [x] Extend `RecordTransactionBundleOut` and internal proposal payload generation to include:
  - [x] `proposed_transaction` details
  - [x] `matched_transactions[]` with all candidates
  - [x] `match_reason` = `same_account_date_amount`
  - [x] Keep schema validation strict and deterministic for response hashing.
- [x] Task 4: Event logging + replay determinism updates (AC: 7, 8)
  - [x] Ensure duplicate-risk proposal path persists deterministic response payload and `output_hash`.
  - [x] Verify event logs include canonical hashes for duplicate-risk-triggered proposals.
- [x] Task 5: Integration and replay tests (AC: 1–8)
  - [x] Add integration tests for:
  - [x] serial transaction writes where subset triggers duplicate-risk proposal and others commit
  - [x] duplicate-risk proposal includes all matched candidates
  - [x] no mutation on duplicate-risk proposal response
  - [x] unchanged idempotent replay for `(source_system, external_id)`
  - [x] Add replay tests to prove identical state+input produce identical duplicate-risk proposal payload and `output_hash`.

## Dev Notes

### Product Decisions Locked for This Story

- Matching uses exact date (no ±N-day window).
- One approval decision is applied per proposed transaction.
- Response includes all potential matched transactions.
- Any writer may approve (authorization model unchanged).
- Gate applies to all transaction writes.

### Current-State Constraints to Preserve

- Approval system is already asynchronous proposal-based (`status="proposed"` then explicit approve/reject tool calls).
- Existing approval gates are policy-threshold/rule based and must continue to function.
- Existing idempotency key is `(source_system, external_id)` and must remain canonical for replay behavior.

### Suggested File Touchpoints

- `src/capital_os/domain/ledger/service.py`
- `src/capital_os/domain/ledger/repository.py`
- `src/capital_os/schemas/tools.py`
- `tests/integration/test_approval_workflow.py`
- `tests/integration/test_record_transaction_bundle.py`
- `tests/replay/test_output_replay.py`

### References

- [Source: `_bmad-output/planning-artifacts/epic-17-duplicate-risk-approval-gate.md`]
- [Source: `_bmad-output/planning-artifacts/epic-4-approval-gates.md`]
- [Source: `initial_prd.md`]
- [Source: `CONSTITUTION.md`]

## Dev Agent Record

### Implementation Plan

- Add deterministic duplicate-risk detection in ledger repository keyed by `date(transaction_date) + account_id + normalized amount`.
- Integrate detection in `record_transaction_bundle` before commit, while preserving existing policy approval/idempotency flow.
- Extend proposed response payload with duplicate-risk context (`proposed_transaction`, `matched_transactions`, `match_reason`) and keep output hash deterministic.
- Add targeted integration/replay/event-log tests for duplicate-risk gating behavior and deterministic replay.

### Debug Log

- Added `find_duplicate_risk_matches` in ledger repository and validated exact-date/normalized-amount behavior with deterministic ordering.
- Updated `record_transaction_bundle` to evaluate duplicate-risk matches pre-commit and route matching writes to proposal path.
- Added deterministic proposal context generation for duplicate-risk-triggered proposals; persisted canonical response payload for replay.
- Expanded `RecordTransactionBundleOut` schema with duplicate-risk fields and strict output shape (`extra="forbid"`).
- Added integration, replay, and event-log tests covering duplicate-risk proposal routing, payload content, no-mutation semantics, replay determinism, and event hash integrity.
- Ran targeted suites for modified areas (all passed).
- Ran full regression suite; all tests passed.
- Senior code review fix: tightened duplicate-risk matching so candidates must contain all normalized `(account_id, amount)` keys from the proposed payload.
- Senior code review fix: removed duplicate-risk N+1 posting fetch path by batching posting hydration for matched transactions.
- Senior code review fix: added explicit serial subset integration coverage (non-matching writes commit while duplicate-risk writes are proposed).
- Senior code review fix: added unit coverage for partial-overlap non-match behavior under all-key matching semantics.
- Re-ran duplicate-risk targeted tests after fixes (`11 passed`).

### Completion Notes

- ✅ AC1/AC2/AC7: duplicate-risk matching executes before commit using exact date + account + normalized amount with deterministic ordering.
- ✅ AC3/AC5/AC6: matching writes now return `status="proposed"` without new ledger rows; non-matching and policy flows remain active; replay by `(source_system, external_id)` remains canonical.
- ✅ AC4: proposal response now includes both proposed transaction details and all matched transaction candidates plus `match_reason`.
- ✅ AC8: duplicate-risk proposal responses are persisted with deterministic `output_hash`; event log entries capture matching output hash.
- ✅ Review remediation: duplicate-risk candidates now require full key-set match (not single-key overlap), reducing false positives while preserving deterministic ordering.
- ✅ Review remediation: serial subset behavior is explicitly covered by integration tests.

### File List

- src/capital_os/domain/ledger/repository.py
- src/capital_os/domain/ledger/service.py
- src/capital_os/schemas/tools.py
- tests/unit/test_duplicate_risk_matching.py
- tests/integration/test_approval_workflow.py
- tests/integration/test_event_log_coverage.py
- tests/replay/test_output_replay.py
- _bmad-output/implementation-artifacts/17-1-duplicate-risk-detection-rule-in-write-path.md

### Change Log

- 2026-03-01: Implemented duplicate-risk approval gate for `record_transaction_bundle`, expanded deterministic proposal payload contract, and added integration/replay/event-log coverage for duplicate-risk behavior.
- 2026-03-01: Fixed CLI completion invocation path in integration harness and aligned read/reconcile numeric assertions with deterministic fixed-precision money output.
- 2026-03-05: Senior review fixes applied: full-key duplicate matching semantics, batched match posting fetch (N+1 removal), serial subset integration coverage, and partial-overlap non-match unit coverage.

### Senior Developer Review (AI)

- Outcome: Changes Requested (addressed in this pass)
- Fixed High findings:
  - Duplicate-risk matching required any overlap key; updated to require full normalized key-set inclusion per candidate transaction.
  - Story task evidence gap for serial subset behavior; added explicit integration test validating commit/propose/commit serial flow.
  - Story File List contained non-17.1 artifacts; list narrowed to actual story implementation/testing files.
- Fixed Medium findings:
  - Duplicate-risk posting hydration used N+1 queries; replaced with single batched posting query.
  - Documentation transparency improved with explicit remediation entries in Debug Log and Change Log.
  - Test evidence refreshed with targeted duplicate-risk run post-fix (`11 passed`).
