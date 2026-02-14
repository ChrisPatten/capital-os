# Playbook: Docs Maintenance

Use this whenever implementation changes behavior, schema, tooling, or backlog status.

## Update Triggers
- New tool added or tool schema changed.
- Domain invariant changed (balancing, idempotency, hashing, timestamps).
- Migration added or trigger behavior changed.
- Tests added/removed that affect requirement coverage.
- Sprint status/backlog priority changes.

## Required Updates
1. Update `docs/current-state.md` for implementation/backlog status.
2. Update `docs/tool-reference.md` for contract or error-model changes.
3. Update `docs/data-model.md` for schema/trigger/invariant changes.
4. Update `docs/testing-matrix.md` for coverage status changes.
5. Update `docs/development-workflow.md` if setup/test/migration flow changed.
6. Update `docs/README.md` if doc structure changed.

## Validation Checklist
1. Every claim in docs maps to existing code/tests/migrations.
2. Dates in docs are current and explicit (`YYYY-MM-DD`).
3. Paths in docs resolve to files in repository.
4. Backlog status statements match `_bmad-output/implementation-artifacts/sprint-status.yaml`.
5. "Not implemented" statements are still true.
