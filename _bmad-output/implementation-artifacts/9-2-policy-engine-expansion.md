# Story 9.2: Policy Engine Expansion

Status: done

## Story

As a risk owner,  
I want approval policy rules to evaluate multiple dimensions beyond amount threshold,  
so that governance decisions reflect entity, category, velocity, risk band, and tool context.

## Acceptance Criteria

1. Add deterministic policy rule model supporting dimensions: `category`, `entity`, `velocity`, `risk_band`, and `tool_type`.
2. Rule evaluation has stable precedence with deterministic tie-break behavior.
3. Proposal-vs-commit outcomes remain deterministic for identical state and input.
4. Policy configuration is validated and rejects invalid rule definitions.

## Tasks / Subtasks

- [x] Task 1: Add policy-rule schema/migration and rollback support (AC: 1, 4)
- [x] Task 2: Implement deterministic rule loader and evaluator with precedence order (AC: 1, 2, 4)
- [x] Task 3: Integrate expanded policy evaluation into write tooling (AC: 1, 3)
- [x] Task 4: Add deterministic integration/replay coverage for multi-dimension rules (AC: 2, 3, 4)

## Notes

- Preserve existing amount-threshold policy as default fallback behavior.
- All decisions must be explainable from persisted rule metadata.

## Dev Agent Record

- Added `policy_rules` table and indexes in `migrations/0006_periods_policies.sql`.
- Implemented deterministic policy evaluation with stable rule precedence:
  - `src/capital_os/domain/policy/service.py`
- Integrated policy decision metadata (`matched_rule_id`, `required_approvals`) into proposal path.
- Added velocity/risk/category/entity/tool-type rule behavior coverage and replay/perf checks:
  - `tests/integration/test_period_policy_controls.py`
  - `tests/perf/test_tool_latency.py`
