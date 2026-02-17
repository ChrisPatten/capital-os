# Testing Matrix

As of 2026-02-16.

## Deterministic Guarantees by Tool

| Tool | Determinism Guarantee | Coverage |
| --- | --- | --- |
| `record_transaction_bundle` | Duplicate `(source_system, external_id)` yields canonical replay hash | `tests/integration/test_idempotency_external_id.py`, `tests/replay/test_output_replay.py` |
| `compute_capital_posture` | Same input yields identical response payload and `output_hash` | `tests/unit/test_posture_engine.py`, `tests/replay/test_output_replay.py` |
| `compute_consolidated_posture` | Same multi-entity input/state yields stable per-entity ordering and deterministic consolidated `output_hash` | `tests/integration/test_consolidated_posture_tool.py`, `tests/replay/test_output_replay.py`, `tests/replay/test_multi_entity_replay.py` |
| `simulate_spend` | Same input yields identical period projections and `output_hash` | `tests/unit/test_simulation_engine.py`, `tests/integration/test_simulation_non_mutation.py`, `tests/replay/test_output_replay.py` |
| `analyze_debt` | Same input yields identical ordering, explainability payload, and `output_hash` | `tests/unit/test_debt_engine.py`, `tests/integration/test_analyze_debt_tool.py`, `tests/replay/test_output_replay.py` |
| `approve_proposed_transaction` | Re-approvals for same proposal replay canonical committed payload/hash | `tests/integration/test_approval_workflow.py`, `tests/replay/test_output_replay.py` |
| `reject_proposed_transaction` | Repeat rejects replay canonical rejected payload/hash | `tests/integration/test_approval_workflow.py`, `tests/replay/test_output_replay.py` |
| `close_period` | Repeat close calls return deterministic idempotent period-state responses | `tests/integration/test_period_policy_controls.py`, `tests/replay/test_output_replay.py` |
| `lock_period` | Repeat lock calls return deterministic idempotent period-state responses | `tests/integration/test_period_policy_controls.py`, `tests/replay/test_output_replay.py` |
| `list_accounts` | Same state/input returns stable page order, cursor behavior, and `output_hash` | `tests/integration/test_read_query_tools.py`, `tests/replay/test_read_query_replay.py` |
| `get_account_tree` | Same state/input returns stable hierarchy ordering and `output_hash` | `tests/integration/test_read_query_tools.py`, `tests/replay/test_read_query_replay.py` |
| `get_account_balances` | Same state/input returns stable source-policy balances and `output_hash` | `tests/integration/test_read_query_tools.py`, `tests/replay/test_read_query_replay.py` |
| `list_transactions` | Same state/input returns stable pagination ordering, cursor behavior, and `output_hash` | `tests/integration/test_epic6_query_surface_tools.py`, `tests/replay/test_query_surface_replay.py` |
| `get_transaction_by_external_id` | Same state/input returns stable transaction/posting payload and `output_hash` | `tests/integration/test_epic6_query_surface_tools.py`, `tests/replay/test_query_surface_replay.py` |
| `list_obligations` | Same state/input returns stable obligation ordering, filters, and `output_hash` | `tests/integration/test_epic6_query_surface_tools.py`, `tests/replay/test_query_surface_replay.py` |
| `list_proposals` | Same state/input returns stable proposal pagination ordering and `output_hash` | `tests/integration/test_epic6_query_surface_tools.py` |
| `get_proposal` | Same state/input returns stable proposal detail/decision ordering and `output_hash` | `tests/integration/test_epic6_query_surface_tools.py` |
| `get_config` | Same state/input returns stable runtime/policy snapshot and `output_hash` | `tests/integration/test_epic6_query_surface_tools.py`, `tests/replay/test_query_surface_replay.py` |
| `propose_config_change` | Duplicate config proposal key returns deterministic proposal replay semantics and `output_hash` | `tests/integration/test_epic6_query_surface_tools.py`, `tests/replay/test_query_surface_replay.py` |
| `approve_config_change` | Repeat approval calls return deterministic applied/already-applied responses and `output_hash` | `tests/integration/test_epic6_query_surface_tools.py` |
| `reconcile_account` | Same state/input returns stable reconciliation payload, proposed-only suggestion, and `output_hash` | `tests/integration/test_reconcile_account_tool.py`, `tests/replay/test_reconciliation_replay.py` |
| `create_account` | Same input produces identical `output_hash`; event log hashes match recomputation | `tests/integration/test_create_account_tool.py`, `tests/replay/test_create_account_replay.py` |

## PRD Criterion Coverage Summary

Detailed SC/FR/NFR mapping lives in `docs/traceability-matrix.md`.

## Security Controls

| Control | Guarantee | Coverage |
| --- | --- | --- |
| Authn baseline | Every `POST /tools/{tool_name}` call requires `x-capital-auth-token` and returns deterministic `401` on absence/invalid token | `tests/security/test_api_security_controls.py` |
| Tool-level authz | Capability map enforcement yields deterministic `403` for denied tools and allow-path coverage for read tools | `tests/security/test_api_security_controls.py` |
| Correlation requirement | `correlation_id` required and validated before handler dispatch for all tools | `tests/security/test_api_security_controls.py`, `tests/integration/test_tool_contract_validation.py` |

## CI Gates

- Full pytest suite: `.github/workflows/ci.yml` job `tests`.
- Migration apply/rollback/re-apply gate: `.github/workflows/ci.yml` job `migration-reversibility`.
- Replay/hash determinism regression gate: `.github/workflows/ci.yml` job `determinism-regression`.
- Security auth surface gate: `.github/workflows/ci.yml` job `security-auth-surface`.
- Performance regression gate includes policy-evaluation overhead p95 `<50ms`: `tests/perf/test_tool_latency.py`.
- Epic 8 multi-entity replay/perf gates: `.github/workflows/ci.yml` job `epic8-multi-entity-gates`.
