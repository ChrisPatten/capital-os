# API Contracts (Core)

## Transport Endpoints

### `GET /health`

- Purpose: readiness check without creating DB side effects.
- Success response: HTTP `200` with `{"status":"ok","timestamp":"<ISO-8601>"}`.
- Failure response: HTTP `503` with `{"status":"down","error":"..."}` in `detail`.

### `POST /tools/{tool_name}`

- Purpose: unified tool execution transport.
- Auth header: `x-capital-auth-token` (required).
- Content type: `application/json`.
- Path param: `tool_name` must map to a registered runtime handler.

## HTTP Error Mapping

- `404`: `unknown_tool`
- `422`: schema/validation failures (`validation_error`)
- `400`: tool execution errors (`error`)
- `500`: event log persistence failures on fail-closed write paths (`event_log_failure`)
- `401`: authentication required
- `403`: forbidden by capability policy

## Registered Tool Names

- `analyze_debt`
- `approve_config_change`
- `approve_proposed_transaction`
- `close_period`
- `compute_capital_posture`
- `compute_consolidated_posture`
- `create_account`
- `create_or_update_obligation`
- `fulfill_obligation`
- `get_account_balances`
- `get_account_tree`
- `get_config`
- `get_proposal`
- `get_transaction_by_external_id`
- `list_accounts`
- `list_obligations`
- `list_proposals`
- `list_transactions`
- `lock_period`
- `propose_config_change`
- `reconcile_account`
- `record_balance_snapshot`
- `record_transaction_bundle`
- `reject_proposed_transaction`
- `simulate_spend`
- `update_account_metadata`
- `update_account_profile`

## Contract Families (Pydantic Schemas)

Tool request/response contracts are defined in `src/capital_os/schemas/tools.py` as `*In` and `*Out` models and validated before tool logic executes.

Examples:

- `RecordTransactionBundleIn` → `RecordTransactionBundleOut`
- `RecordBalanceSnapshotIn` → `RecordBalanceSnapshotOut`
- `CreateOrUpdateObligationIn` → `CreateOrUpdateObligationOut`
- `ListTransactionsIn` → `ListTransactionsOut`
- `GetTransactionByExternalIdIn` → `GetTransactionByExternalIdOut`

## Security and Determinism Headers/Fields

- Request auth: `x-capital-auth-token`
- Correlation ID: required in payload as `correlation_id`; additional header match is enforced for `update_account_profile`.
- Observability fields produced per invocation include `input_hash`, `output_hash`, status, and duration.
