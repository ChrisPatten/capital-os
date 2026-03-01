# Epic 17: Duplicate-Risk Approval Gate for Transaction Writes (FR-03 extension)

## Goal
Reduce accidental duplicate transaction entries by requiring explicit approval when a proposed write matches prior transactions on exact duplicate-risk dimensions, while preserving current proposal/approval and idempotency behavior.

### Story 17.1: Duplicate-Risk Detection Rule in Write Path
- Add duplicate-risk detection for `record_transaction_bundle` using exact `account_id + effective_date + normalized amount (4dp)`.
- Apply rule to all transaction writes.
- Return all potential matches for a single proposed transaction.

### Story 17.2: Proposal Contract and Approval Decision Expansion
- When duplicate-risk matches exist, return `status="proposed"` and block immediate ledger mutation.
- Include both sides in response payload: proposed transaction detail + all matched transaction details.
- Preserve one approval decision per proposed transaction and existing approve/reject tool semantics.

### Story 17.3: Authorization, Audit, and Determinism Coverage
- Allow any writer to approve duplicate-risk proposals.
- Log duplicate-risk trigger and decision outcomes with deterministic hashes and correlation IDs.
- Add integration/replay tests for serial write behavior, match payload determinism, and non-mutating reject flows.
