# Epic 10: API Security and Runtime Controls (FR-28..FR-30, NFR-09, NFR-11)

## Goal
Guarantee authenticated, authorized, correlated, and no-egress tool execution.

### Story 10.1: Authentication Baseline
- Require authenticated identity for all tool calls.
- Attach actor context to request lifecycle and event logs.

### Story 10.2: Tool-Level Authorization and Correlation Integrity
- Enforce capability checks per tool.
- Require `correlation_id` for all tool invocations.

### Story 10.3: No-Egress Enforcement and Security Test Coverage
- Add runtime guardrails blocking outbound network egress.
- Add telemetry + tests proving 100% auth coverage and no-egress compliance.
