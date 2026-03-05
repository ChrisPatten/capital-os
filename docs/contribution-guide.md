# Contribution Guide

## Development Standards

- Keep ledger invariants and deterministic behavior intact.
- Use numbered migrations with paired rollback scripts.
- Maintain append-only protections and write-boundary constraints.

## Change Workflow

1. Implement changes in domain/tool boundaries.
2. Add or update tests in relevant suites (`unit`, `integration`, `replay`, `security`, `perf`).
3. Run `pytest` and targeted suites for touched surfaces.
4. Validate migrations with `scripts/check_migration_cycle.py` when schema changes are involved.

## Documentation Expectations

- Update docs for API or schema changes.
- Keep `docs/tool-reference.md` and architectural references synchronized.
- Prefer task-oriented updates with precise paths and commands.

## Quality Gates

- Deterministic replay tests should pass for touched tool surfaces.
- Security controls (auth, role boundaries, append-only triggers) must remain enforced.
- Performance checks should not regress p95 guardrails in perf tests.
