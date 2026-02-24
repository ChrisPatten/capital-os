---
name: capital-os
description: Deterministic double-entry ledger core. Record transactions, snapshots, and obligations; compute posture; query balances — all via the local CLI (no HTTP server required).
metadata: {"openclaw": {"emoji": "📒", "requires": {"bins": ["capital-os"]}, "install": [{"id": "pip", "kind": "download", "label": "pip install -e . (from repo root)"}]}}
---

# Capital OS — Ledger Core

Capital OS is a local-first, deterministic financial truth layer. Use the trusted local CLI (`capital-os`) to call tools directly — no HTTP server, no auth token required. All schema validation, event logging, and ledger invariants are enforced identically to the HTTP adapter.

## Installation

```bash
# From the repo root:
pip install -e .

# Or with pipx (isolated environment):
pipx install .

# Verify:
capital-os health
```

## Invoking tools

```bash
# Call any tool with inline JSON:
capital-os tool call <tool_name> --json '<payload>'

# Call with a JSON file:
capital-os tool call <tool_name> --json @payload.json

# Call from stdin:
echo '<payload>' | capital-os tool call <tool_name>

# Target a specific database file:
capital-os tool call <tool_name> --json '<payload>' --db-path /path/to/capital_os.db
```

Success: canonical JSON on stdout, exit code `0`.
Failure: structured `{"error": "...", "message": "..."}` on stderr, exit code `1`.

## Discovery

```bash
capital-os health                          # DB readiness check
capital-os tool list                       # all registered tools + read/write classification
capital-os tool schema <tool_name>         # input/output schema for a tool
capital-os tool call --help                # full flag reference
```

## Bootstrap (first run)

```bash
make init           # apply migrations + seed initial chart of accounts (idempotent)
capital-os health   # confirm DB is ready
```

## Core invariants

- USD only for all postings and snapshots.
- `record_transaction_bundle` requires ≥2 postings and MUST balance: `sum(amount) == 0` after 4 dp normalization.
- Idempotency key for transactions: `(source_system, external_id)` — duplicates return `status="idempotent-replay"`.
- Always supply a unique `correlation_id` per call.
- Never include secrets or secret-like strings in payloads.
- Never write to SQLite directly — all writes must go through tool calls.

## Workflow: loading data (MVP order)

### Step 0 — Ensure chart of accounts exists

```bash
make init
capital-os tool call list_accounts --json '{"correlation_id": "init-check-001"}'
```

To create accounts at runtime:

```bash
capital-os tool call create_account --json '{
  "code": "1310",
  "name": "Checking Account",
  "account_type": "asset",
  "correlation_id": "setup-acct-001"
}'
```

### Step 1 — Record balance snapshots (quickest)

Upserts by `(account_id, snapshot_date)`:

```bash
capital-os tool call record_balance_snapshot --json '{
  "source_system": "manual",
  "account_id": "<account_id>",
  "snapshot_date": "2026-02-23",
  "balance": "15297.2100",
  "currency": "USD",
  "correlation_id": "snap-001"
}'
```

### Step 2 — Record obligations (due dates)

Upserts by `(source_system, name, account_id)`:

```bash
capital-os tool call create_or_update_obligation --json '{
  "source_system": "manual",
  "name": "rent",
  "account_id": "<account_id>",
  "cadence": "monthly",
  "expected_amount": "3200.0000",
  "currency": "USD",
  "next_due_date": "2026-03-01",
  "correlation_id": "obl-001"
}'
```

### Step 3 — Record transactions (double-entry)

```bash
capital-os tool call record_transaction_bundle --json '{
  "source_system": "manual",
  "external_id": "tx-2026-02-23-dinner",
  "date": "2026-02-23T19:05:00Z",
  "description": "Dinner",
  "postings": [
    {"account_id": "<expense_account_id>", "amount": "45.1200", "currency": "USD"},
    {"account_id": "<liability_account_id>", "amount": "-45.1200", "currency": "USD"}
  ],
  "correlation_id": "txn-001"
}'
```

If the response has `status="proposed"`, the transaction was NOT committed (approval policy triggered). Follow up with:

```bash
capital-os tool call approve_proposed_transaction --json '{
  "proposal_id": "<proposal_id>",
  "reason": "approved",
  "correlation_id": "approve-001"
}'
```

## Verification queries

```bash
# Account structure
capital-os tool call list_accounts --json '{"correlation_id": "q-001"}'
capital-os tool call get_account_tree --json '{"correlation_id": "q-002"}'

# Balances as-of a date (ledger | snapshot | best_available)
capital-os tool call get_account_balances --json '{
  "as_of_date": "2026-02-23",
  "source_policy": "best_available",
  "correlation_id": "q-003"
}'

# Transaction history
capital-os tool call list_transactions --json '{"correlation_id": "q-004"}'
capital-os tool call get_transaction_by_external_id --json '{
  "source_system": "manual",
  "external_id": "tx-2026-02-23-dinner",
  "correlation_id": "q-005"
}'

# Upcoming obligations
capital-os tool call list_obligations --json '{"active_only": true, "correlation_id": "q-006"}'
```

## Account metadata update (merge-patch)

Keys overwrite, `null` removes, unmentioned keys are preserved:

```bash
capital-os tool call update_account_metadata --json '{
  "account_id": "<account_id>",
  "metadata": {"institution": "Chase", "obsolete_key": null},
  "correlation_id": "meta-001"
}'
```

## Error handling

| Exit code | Meaning |
|-----------|---------|
| `0` | Success — parse stdout as JSON |
| `1` | Failure — parse stderr as `{"error": "...", "message": "..."}` |

Key error codes in the payload:
- `validation_error` — schema mismatch; fix payload and retry.
- `tool_execution_error` — domain or DB error; treat as no commit unless `status="committed"` was returned.
- `tool_not_found` — unknown tool name.

## Using the HTTP adapter instead

If the HTTP server is needed (e.g. remote agents, MCP):

```bash
make serve-idle        # idempotent start; auto-stops after inactivity
# Then call: POST http://127.0.0.1:8000/tools/<tool_name>
# Headers: x-capital-auth-token: dev-admin-token
# Body: {... , "correlation_id": "<unique>"}
make stop
```

## Determinism notes

- Supply all dates as explicit UTC ISO 8601 strings.
- Use 4 dp decimal strings for monetary values (`"45.1200"` not `45.12`).
- Use stable `external_id` values (hash of source artifact + line item id is ideal).
- Identical stored state + identical input always produces identical `output_hash`.
