# Testing Matrix

As of 2026-02-14. This maps PRD success criteria/FR/NFR items to current tests.

## Success Criteria Coverage

| Criterion | Current Status | Evidence |
| --- | --- | --- |
| SC-01 Ledger balance integrity | Partial | `tests/integration/test_record_transaction_bundle.py`, `tests/unit/test_invariants.py` |
| SC-02 Deterministic outputs | Partial | `tests/replay/test_output_replay.py`, `tests/unit/test_hashing.py`, `tests/unit/test_posture_engine.py` |
| SC-03 Tool trace completeness | Partial | `tests/integration/test_event_log_coverage.py` |
| SC-04 Replayability | Partial | `tests/replay/test_output_replay.py` |
| SC-05 Approval enforcement | Not implemented | No approval-gate tests yet (Epic 4 backlog) |
| SC-06 Zero external egress | Not covered by tests | No runtime egress-deny test currently |
| SC-07 p95 latency <300ms | Partial (smoke) | `tests/perf/test_tool_latency.py` |

## Functional Requirement Coverage

| FR | Requirement | Current Status | Evidence |
| --- | --- | --- | --- |
| FR-01 | Account hierarchy management | Implemented + tested | `tests/integration/test_accounts_hierarchy.py` |
| FR-02 | Record balanced transaction bundles | Implemented + tested | `tests/integration/test_record_transaction_bundle.py` |
| FR-03 | Idempotent transaction recording | Implemented + tested | `tests/integration/test_idempotency_external_id.py` |
| FR-04 | Record balance snapshots | Implemented (limited direct integration assertions) | `src/capital_os/domain/ledger/service.py`, `src/capital_os/tools/record_balance_snapshot.py` |
| FR-05 | Track obligations | Implemented (limited direct integration assertions) | `src/capital_os/domain/ledger/service.py`, `src/capital_os/tools/create_or_update_obligation.py` |
| FR-06 | Compute capital posture | Implemented + tested | `tests/unit/test_posture_engine.py`, `tests/integration/test_event_log_coverage.py` |
| FR-07 | Simulate spend (non-mutating) | Implemented + tested | `tests/unit/test_simulation_engine.py`, `tests/integration/test_simulation_non_mutation.py`, `tests/integration/test_tool_contract_validation.py` |
| FR-08 | Debt optimization analysis | Not implemented | Epic 3 backlog |
| FR-09 | Structured tool API validation | Implemented + tested | `tests/integration/test_tool_contract_validation.py` |
| FR-10 | Tool invocation logging | Implemented + tested | `tests/integration/test_event_log_coverage.py` |
| FR-11 | Approval gates for high-impact writes | Not implemented | Epic 4 backlog |
| FR-12 | Privilege boundaries | Implemented + tested | `tests/security/test_db_role_boundaries.py` |

## Non-Functional Requirement Coverage

| NFR | Requirement | Current Status | Evidence |
| --- | --- | --- | --- |
| NFR-01 | Determinism | Partial | `tests/replay/test_output_replay.py`, `tests/unit/test_hashing.py` |
| NFR-02 | ACID transactionality | Partial | Write paths use `transaction()` and rollback semantics are exercised in integration tests |
| NFR-03 | Performance p95 <300ms on reference dataset | Partial (not full reference dataset) | `tests/perf/test_tool_latency.py` |
| NFR-04 | Observability via correlation_id | Partial | `tests/integration/test_event_log_coverage.py` |
| NFR-05 | Runtime isolation (no external calls) | Not covered by tests | No egress tests |
| NFR-06 | Reversible migrations in CI | Partial (scripts exist, CI gate not implemented) | `migrations/*.rollback.sql`, `tests/conftest.py` reset pattern |
| NFR-07 | Financial math branch coverage | Partial | Unit tests exist; no enforced branch coverage threshold in config |

## Gaps to Prioritize
- Add integration tests explicitly for `record_balance_snapshot` and `create_or_update_obligation` behavior.
- Add migration forward/rollback/re-apply CI gate (Epic 5).
- Add explicit no-egress safety test for runtime constraints.
- Add higher-scale perf harness aligned to PRD reference dataset size.
