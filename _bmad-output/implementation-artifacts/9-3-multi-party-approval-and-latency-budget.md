# Story 9.3: Multi-Party Approval and Latency Budget

Status: done

## Story

As a compliance lead,  
I want optional multi-party approval semantics with strict latency controls,  
so that high-risk actions require multiple approvers without violating runtime performance targets.

## Acceptance Criteria

1. Support configurable required approver count for approval-gated proposals.
2. Enforce distinct approver identity tracking for multi-party approvals.
3. Commit occurs exactly once when required approvals are satisfied; intermediate approvals remain proposal state.
4. Policy evaluation overhead remains below `<50ms` p95 in perf test coverage.

## Tasks / Subtasks

- [x] Task 1: Extend proposal/decision schema for multi-party state and rollback support (AC: 1, 2, 3)
- [x] Task 2: Implement approval service workflow for incremental approvals and final commit (AC: 1, 2, 3)
- [x] Task 3: Add deterministic concurrency/replay tests for multi-party approvals (AC: 2, 3)
- [x] Task 4: Add policy-latency perf gate for expanded policy engine (AC: 4)

## Notes

- Must preserve idempotency and append-only guarantees of proposal/decision history.
- Keep compatibility for single-approver policies (`required_approvals=1`).

## Dev Agent Record

- Extended approval persistence to support multi-party semantics:
  - `approval_proposals.required_approvals`
  - `approval_proposals.matched_rule_id`
  - `approval_decisions.approver_id`
  - unique distinct-approver index
- Implemented incremental approval workflow with deterministic pending response and exactly-once commit.
- Added concurrency and deterministic replay tests for duplicate approver behavior and final quorum commit.
- Added policy evaluation p95 perf assertion (`<50ms`) in `tests/perf/test_tool_latency.py`.
