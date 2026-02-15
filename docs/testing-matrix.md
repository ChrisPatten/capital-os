# Testing Matrix

As of 2026-02-15.

## Deterministic Guarantees by Tool

| Tool | Determinism Guarantee | Coverage |
| --- | --- | --- |
| `record_transaction_bundle` | Duplicate `(source_system, external_id)` yields canonical replay hash | `tests/integration/test_idempotency_external_id.py`, `tests/replay/test_output_replay.py` |
| `compute_capital_posture` | Same input yields identical response payload and `output_hash` | `tests/unit/test_posture_engine.py`, `tests/replay/test_output_replay.py` |
| `simulate_spend` | Same input yields identical period projections and `output_hash` | `tests/unit/test_simulation_engine.py`, `tests/integration/test_simulation_non_mutation.py`, `tests/replay/test_output_replay.py` |
| `analyze_debt` | Same input yields identical ordering, explainability payload, and `output_hash` | `tests/unit/test_debt_engine.py`, `tests/integration/test_analyze_debt_tool.py`, `tests/replay/test_output_replay.py` |
| `approve_proposed_transaction` | Re-approvals for same proposal replay canonical committed payload/hash | `tests/integration/test_approval_workflow.py`, `tests/replay/test_output_replay.py` |
| `reject_proposed_transaction` | Repeat rejects replay canonical rejected payload/hash | `tests/integration/test_approval_workflow.py`, `tests/replay/test_output_replay.py` |
| `list_accounts` | Same state/input returns stable page order, cursor behavior, and `output_hash` | `tests/integration/test_read_query_tools.py`, `tests/replay/test_read_query_replay.py` |
| `get_account_tree` | Same state/input returns stable hierarchy ordering and `output_hash` | `tests/integration/test_read_query_tools.py`, `tests/replay/test_read_query_replay.py` |
| `get_account_balances` | Same state/input returns stable source-policy balances and `output_hash` | `tests/integration/test_read_query_tools.py`, `tests/replay/test_read_query_replay.py` |

## PRD Criterion Coverage Summary

Detailed SC/FR/NFR mapping lives in `docs/traceability-matrix.md`.

## CI Gates

- Full pytest suite: `.github/workflows/ci.yml` job `tests`.
- Migration apply/rollback/re-apply gate: `.github/workflows/ci.yml` job `migration-reversibility`.
- Replay/hash determinism regression gate: `.github/workflows/ci.yml` job `determinism-regression`.
