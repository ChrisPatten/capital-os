# MVP Bootstrap and Agent Testing

Last updated: 2026-02-16

This runbook provides a deterministic, one-command smoke flow for agent-driven API writes and reads.

## Environment Setup
- Python 3.11+
- Install dependencies:
```bash
pip install -e ".[dev]"
```
- Default auth token for smoke and local admin calls:
```bash
export CAPITAL_OS_AUTH_TOKEN="${CAPITAL_OS_AUTH_TOKEN:-dev-admin-token}"
```
- Optional database override (default shown):
```bash
export CAPITAL_OS_DB_URL="${CAPITAL_OS_DB_URL:-sqlite:///./data/capital_os.db}"
```

## One-Command Smoke Workflow
Run:
```bash
make mvp-smoke
```

The workflow executes these steps in order:
1. Stop any running local runtime.
2. Reset SQLite DB file from `CAPITAL_OS_DB_URL`.
3. Apply migrations.
4. Seed COA from `config/coa.yaml`.
5. Start API runtime and verify `/health`.
6. Invoke representative write tools:
   - `record_transaction_bundle` (plus idempotent replay check)
   - `record_balance_snapshot`
   - `create_or_update_obligation`
7. Invoke representative read tools and assert persisted state:
   - `list_accounts`
   - `list_transactions`
   - `get_transaction_by_external_id`
   - `list_obligations`
   - `get_account_balances`
8. Stop runtime.

## Expected Success Signatures
- Final line:
```text
[mvp-smoke] SUCCESS: deterministic smoke flow completed
```
- Exit code: `0`

## Failure Signatures and Recovery
- Failure format:
```text
[mvp-smoke] FAILURE in step '<step-name>': <cause>
```
- Exit code: non-zero.

Common failures and actions:
- `db-reset`: invalid/non-SQLite `CAPITAL_OS_DB_URL`.
  - Use a SQLite URL, e.g. `sqlite:///./data/capital_os.db`.
- `start-runtime` or `api-health`: runtime failed to bind/boot.
  - Check `.run/uvicorn.log`, then rerun `make stop` and `make mvp-smoke`.
- `write-*` or `read-*`: tool contract/auth mismatch.
  - Verify `CAPITAL_OS_AUTH_TOKEN` and rerun with default admin token.

## Scope Note (Epic 11 Deferred)
This MVP smoke flow validates bootstrap and agent tool-path operability only.

Full portability features from Epic 11 remain deferred, including:
- Ledger export with integrity markers.
- Controlled import (`dry-run` and strict modes).
- Admin backup/restore workflows.
