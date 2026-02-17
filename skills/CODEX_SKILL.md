# SKILL: capital-os (Ledger Core Tool API)

## Purpose
Use Capital OS as the canonical, auditable ledger core. Interact only through the HTTP tool interface:
- `GET /health`
- `POST /tools/{tool_name}`

Do NOT write to the SQLite DB directly. All writes must go through tool endpoints.

## Runtime assumptions
- Service auth header: `x-capital-auth-token` (required for all tools).
- Every tool call MUST include `correlation_id` (regex: `^[A-Za-z0-9._:-]{1,128}$`).
- USD only for ledger postings and snapshots.
- Idempotency for `record_transaction_bundle` is `(source_system, external_id)`.

## Make-based lifecycle (repo convention)
This repo is intended to be driven by `make` targets so an agent can:
1) start the API if not running
2) call endpoints
3) auto-shutdown after inactivity

### Targets

- `make serve-idle`
  - Idempotent server start:
    - First call `GET /health`; if healthy, do nothing and return success.
    - If not healthy, start server in background and return success once `GET /health` is OK.
  - Auto-shutdown:
    - After N minutes of no tool calls (or no HTTP requests), gracefully stop the server.

- `make stop`
  - Stops the running server process if present.

### Agent boot behavior
Before any tool call:
1) `GET /health`
2) If not `{"status":"ok"}`, run `make serve-idle`
3) Retry `GET /health`

## Authentication / capabilities
Default dev tokens (unless overridden by env):
- `dev-admin-token`: `tools:read`, `tools:write`, `tools:approve`, `tools:admin`
- `dev-reader-token`: `tools:read`

Tool authorization is capability-based and defaults to deny when unmapped.

## Tool endpoint contract
- URL: `POST /tools/{tool_name}`
- Header: `x-capital-auth-token: <token>`
- JSON body: tool-specific schema + `correlation_id`

Error semantics (high-signal):
- `404` unknown tool
- `401` missing/invalid auth token
- `403` capability denied
- `422` schema/validation error (deterministic, sanitized)
- `400` tool execution error

## Account management

### Create accounts at runtime
Use `create_account` to add new accounts to the chart of accounts:
- Required: `code`, `name`, `account_type` (asset/liability/equity/income/expense), `correlation_id`
- Optional: `parent_account_id`, `entity_id`, `metadata`
- Returns `account_id` and `status: "committed"` on success
- Capability: `tools:write`

Example:
```bash
curl -sS -H "x-capital-auth-token: $TOKEN" \
  -H "content-type: application/json" \
  "$CAPOS/tools/create_account" \
  -d '{
    "code": "1310",
    "name": "New Checking Account",
    "account_type": "asset",
    "parent_account_id": "acct-checking",
    "metadata": {"institution": "Chase"},
    "correlation_id": "capos.create_account.20260216.a1"
  }'
```

## Minimal "put data into it" workflow (MVP)

### 1) Record balance snapshots (quickest value)
Use `record_balance_snapshot` to store point-in-time balances by `(account_id, snapshot_date)` (upsert).

### 2) Create obligations (due dates / expected amounts)
Use `create_or_update_obligation` (upsert by `(source_system, name, account_id)`).

### 3) Record ledger transactions (double-entry)
Use `record_transaction_bundle` with at least 2 postings, sum(amount)==0 after 4dp normalization, USD.

Important: this tool can return `status="proposed"` (no mutation) when policy requires approval.

- If proposed: call `approve_proposed_transaction`
- Or: `reject_proposed_transaction`

## Correlation IDs and external IDs
- Always generate a unique `correlation_id` per call (e.g., `capos.<yyyymmdd>.<shortid>`).
- Always generate stable `external_id` for idempotent writes (e.g., hash of source artifact + line item id).

## Examples (curl)
Set:
- `CAPOS=http://127.0.0.1:8000`
- `TOKEN=dev-admin-token`

Health:
```bash
curl -sS "$CAPOS/health"

# List accounts:
curl -sS -H "x-capital-auth-token: $TOKEN" \
  -H "content-type: application/json" \
  "$CAPOS/tools/list_accounts" \
  -d '{"limit":50,"correlation_id":"capos.list_accounts.20260216.a1"}'

# Record snapshot:
curl -sS -H "x-capital-auth-token: $TOKEN" \
  -H "content-type: application/json" \
  "$CAPOS/tools/record_balance_snapshot" \
  -d '{
    "source_system":"manual",
    "account_id":"acct-checking",
    "snapshot_date":"2026-02-16",
    "balance":"15297.2100",
    "currency":"USD",
    "correlation_id":"capos.snapshot.20260216.a1"
  }'

# Record transaction bundle:
curl -sS -H "x-capital-auth-token: $TOKEN" \
  -H "content-type: application/json" \
  "$CAPOS/tools/record_transaction_bundle" \
  -d '{
    "source_system":"manual",
    "external_id":"manual-2026-02-16-dinner-0001",
    "date":"2026-02-16T19:05:00Z",
    "description":"Dinner",
    "postings":[
      {"account_id":"acct-expenses-dining","amount":"45.1200","currency":"USD"},
      {"account_id":"acct-liabilities-amex","amount":"-45.1200","currency":"USD"}
    ],
    "correlation_id":"capos.txn.20260216.a1"
  }'

# Approve proposal (if the prior call returned status="proposed" + proposal_id):
curl -sS -H "x-capital-auth-token: $TOKEN" \
  -H "content-type: application/json" \
  "$CAPOS/tools/approve_proposed_transaction" \
  -d '{
    "proposal_id":"prop_123",
    "reason":"approve",
    "correlation_id":"capos.approve.20260216.a1"
  }'
```

## Safety / guardrails
* Never include secrets in payloads (IDs should not look like tokens/passwords). 
* Never attempt DB writes outside tool layer.
* For write tools, treat 422/400/500 as “no commit” unless the tool explicitly returned status="committed".
* Prefer snapshots/obligations first; transaction-level ingestion can come later.
