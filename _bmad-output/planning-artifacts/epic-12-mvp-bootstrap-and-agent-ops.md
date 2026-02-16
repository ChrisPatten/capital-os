# Epic 12: MVP Bootstrap and Agent Operations Enablement

## Goal
Enable immediate end-to-end MVP testing by providing deterministic bootstrap, local runtime controls, and a repeatable agent-driven API smoke path, without waiting for full Epic 11 portability features.

## Why This Epic Exists
- Epic 11 targets full portability/recoverability controls (`export_ledger`, transaction-bundle import, backup/restore).
- MVP testing needs a narrower path now:
  - seed a valid Chart of Accounts once
  - run API reliably in agent loops
  - verify write/read tool flow end-to-end

This epic is explicitly a delivery accelerator and does not replace Epic 11.

## Scope Boundaries
- In scope:
  - Bootstrap-only COA seeding from `config/coa.yaml` (direct DB upsert allowed for initialization/reset flows).
  - Makefile developer/operator workflow for migrate/seed/run/serve-idle/health/stop.
  - Deterministic smoke workflow proving agent can build data through existing API tools.
- Out of scope:
  - `export_ledger`
  - `import_transaction_bundles(dry_run, strict)`
  - admin backup/restore lifecycle

## Story 12.1: Bootstrap COA Seed Path (Admin Utility)
- Deliver a validated COA import utility using `config/coa.yaml`.
- Support idempotent upsert semantics for accounts:
  - create missing
  - update safe fields only (name/metadata/parent/is_active policy-controlled)
  - never delete
- Treat COA file as bootstrap/reset input only; post-bootstrap account governance remains tool/API-driven.

Acceptance Criteria:
- `coa-validate` catches:
  - duplicate `account_id`
  - invalid `type`
  - missing parent refs
  - parent cycles
- `coa-seed` is idempotent across repeated runs.
- Existing DB accounts not present in YAML are never deleted and produce warning-level visibility.

## Story 12.2: Makefile Runtime Controls and Idempotent Serve
- Add Makefile targets and conventions:
  - `make init` -> `make migrate` + `make coa-seed`
  - `make migrate`
  - `make coa-validate`
  - `make coa-seed`
  - `make health`
  - `make run`
  - `make stop`
  - `make serve-idle`
- Respect runtime files in `.run/`:
  - `.run/capital-os.pid`
  - `.run/capital-os.url`
  - `.run/last_request.ts`
  - `.run/uvicorn.log`
- `serve-idle` semantics:
  - health-first idempotence (exit 0 if already healthy)
  - stale PID file must not block startup
  - idle timeout shutdown using `CAPITAL_OS_IDLE_SECONDS`

Acceptance Criteria:
- Repeated `make serve-idle` calls are safe no-op when service is already healthy.
- Wrapper process exits service after configured idle window with no requests.
- `make stop` cleans runtime state files.

## Story 12.3: MVP Agent Smoke Flow and Runbook
- Add a one-command smoke path that verifies:
  - DB reset/migration
  - COA seed
  - API start + health
  - representative write tool calls (`record_transaction_bundle`, `record_balance_snapshot`, `create_or_update_obligation`)
  - representative read tool calls confirming persisted state
- Capture minimal runbook for agent operators:
  - bootstrap commands
  - auth token setup
  - expected success/failure signatures

Acceptance Criteria:
- Smoke workflow is deterministic and passes repeatedly on clean DB.
- Failures are actionable (clear exit code and step-level error output).
- Documentation states Epic 11 features are intentionally deferred.

## Dependencies
- Depends on existing migrations and core write/read tool availability.
- Should not block Epic 11 implementation; it de-risks it by enabling earlier usage feedback.

## Exit Criteria for MVP Readiness
1. New environment can be bootstrapped with `make init`.
2. Agent can call API to create realistic ledger data with existing tools.
3. Runtime can be started/stopped safely in repeated automated loops (`serve-idle` idempotence).
