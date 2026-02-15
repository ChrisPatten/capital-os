# Epic 9: Period Control and Policy Engine Expansion (FR-24..FR-27, NFR-12)

## Goal
Enforce accounting period integrity and generalized policy-based approvals.

### Story 9.1: Close/Lock Period and Adjusting Entries
- Implement `close_period(period)` and `lock_period(period)`.
- Add adjusting-entry tagging with explicit reason codes.

### Story 9.2: Policy Rule Expansion
- Extend gating rules to category/entity/velocity/risk-band/tool-type dimensions.
- Preserve deterministic proposal-vs-commit decisions.

### Story 9.3: Multi-Party Approval and Latency Budget
- Add optional multi-approver workflow semantics.
- Ensure policy engine adds <50ms p95 latency.
