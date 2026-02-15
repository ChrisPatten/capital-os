# Epic 7: Reconciliation and Source-of-Truth Policy (FR-19..FR-20)

## Goal
Provide deterministic reconciliation outputs and configurable truth-selection behavior.

### Story 7.1: Reconciliation Domain and Tool
- Implement `reconcile_account(account_id, as_of_date, method)`.
- Return `ledger_balance`, `snapshot_balance`, `delta`, and `suggested_adjustment_bundle` (proposed only).

### Story 7.2: Truth Selection Policy Wiring
- Add `balance_source_policy` config with `ledger_only|snapshot_only|best_available`.
- Ensure retrieval tools and posture inputs respect configured policy.

### Story 7.3: Reconciliation Determinism and Replay Tests
- Add replay coverage for reconciliation outputs.
- Verify adjustment suggestions are deterministic and never auto-committed.
