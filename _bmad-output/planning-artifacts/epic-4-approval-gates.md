# Epic 4: Approval-Gated Writes (FR-11)

## Goal
Enforce proposal/approval workflow for high-impact write operations.

### Story 4.1: Approval Policy and Schema
- Add configurable approval threshold and proposal entity lifecycle.
- Ensure above-threshold writes return `status=\"proposed\"` without mutation.

### Story 4.2: Proposal and Approval Tools
- Implement proposal + approve/reject tool paths.
- Ensure approval idempotency and exactly one canonical commit.

### Story 4.3: Approval Transactionality and Audit
- Enforce fail-closed event logging in same write transaction.
- Add concurrency tests for duplicate approve/replay behavior.
