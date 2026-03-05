---
name: capital-os
description: Deterministic double-entry ledger core. Record transactions, snapshots, and obligations; compute posture; query balances — all via the local CLI (no HTTP server required).
metadata: {"openclaw": {"emoji": "📒", "requires": {"bins": ["capital-os"]}}}
---

# Capital OS — Ledger Core

Capital OS is a local-first, deterministic financial truth layer. Use the trusted local CLI (`capital-os`) to call tools directly — no HTTP server, no auth token required. All schema validation, event logging, and ledger invariants are enforced identically to the HTTP adapter.


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
  "next_due_date": "2026-03-01",
  "correlation_id": "obl-001"
}'
```

To deactivate an obligation directly (e.g. cancelled before payment), pass `"active": false`.

### Step 2a — Mark an obligation as paid (`fulfill_obligation`)

When a payment is made, record the transaction first, then link it to the obligation:

```bash
# 1. Record the payment transaction
capital-os tool call record_transaction_bundle --json '{
  "source_system": "manual",
  "external_id": "rent-2026-03-01",
  "date": "2026-03-01T00:00:00Z",
  "description": "March rent payment",
  "postings": [
    {"account_id": "<liability_account_id>", "amount": "3187.5000", "currency": "USD"},
    {"account_id": "<asset_account_id>",    "amount": "-3187.5000", "currency": "USD"}
  ],
  "correlation_id": "txn-rent-mar"
}'

# 2. Fulfill the obligation, linking the transaction
capital-os tool call fulfill_obligation --json '{
  "obligation_id": "<obligation_id>",
  "fulfilled_by_transaction_id": "<transaction_id from step 1>",
  "correlation_id": "obl-fulfill-001"
}'
```

Response:
- `status`: `"fulfilled"` on success, `"already_fulfilled"` if called again (idempotent).
- `fulfilled_by_transaction_id`: the linked transaction ID.
- `fulfilled_at`: UTC timestamp recorded at fulfillment.

Omit `fulfilled_by_transaction_id` to deactivate without linking a payment (e.g. obligation was waived).

To true up the estimated amount before fulfilling:

```bash
capital-os tool call create_or_update_obligation --json '{
  "source_system": "manual",
  "name": "rent",
  "account_id": "<account_id>",
  "cadence": "monthly",
  "expected_amount": "3187.5000",
  "next_due_date": "2026-03-01",
  "correlation_id": "obl-trueup-001"
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

# Fulfilled/inactive obligations
capital-os tool call list_obligations --json '{"active_only": false, "correlation_id": "q-007"}'
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

## Account profile updates (renames + suffix/reference evolution)

Use `update_account_profile` for normal single-account rename/profile maintenance.

```bash
capital-os tool call update_account_profile --json '{
  "account_id": "<account_id>",
  "display_name": "Primary Checking",
  "institution_name": "River Credit Union",
  "institution_suffix": "SFX-2026-A",
  "source_system": "manual",
  "external_id": "acct-profile-2026-03-05-001",
  "correlation_id": "acct-profile-001"
}'
```

Notes:
- Idempotency key: `(source_system, external_id)`.
- Duplicate idempotency keys return the canonical prior response.
- Identifier/suffix history is persisted automatically and read via direct SQL in Phase 1.

### Identifier history SQL

```sql
-- Active identifier row
SELECT account_id, source_system, external_id, institution_suffix, valid_from, valid_to
FROM account_identifier_history
WHERE account_id = :account_id
  AND source_system = :source_system
  AND valid_to IS NULL;

-- Full history timeline
SELECT account_id, source_system, external_id, institution_suffix, valid_from, valid_to, correlation_id
FROM account_identifier_history
WHERE account_id = :account_id
  AND source_system = :source_system
ORDER BY valid_from ASC, history_id ASC;
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

## Determinism notes

- Supply all dates as explicit UTC ISO 8601 strings.
- Use 4 dp decimal strings for monetary values (`"45.1200"` not `45.12`).
- Use stable `external_id` values (hash of source artifact + line item id is ideal).
- Identical stored state + identical input always produces identical `output_hash`.
