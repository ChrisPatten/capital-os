# Epic 10: API Security and Runtime Controls (FR-28..FR-30, NFR-09)

## Goal
Guarantee authenticated, authorized, and correlated tool execution.

### Story 10.1: Authentication Baseline
- Require authenticated identity for all tool calls.
- Attach actor context to request lifecycle and event logs.

### Story 10.2: Tool-Level Authorization and Correlation Integrity
- Enforce capability checks per tool.
- Require `correlation_id` for all tool invocations.

### Story 10.3: Security Coverage Adjustment and No-Egress Rollback
- Remove runtime no-egress guardrails from tool execution.
- Keep telemetry + tests proving auth/authz/correlation compliance.
