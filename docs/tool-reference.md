# Tool Reference

As of 2026-02-23, the service exposes both an HTTP API (`POST /tools/{tool_name}`) and a trusted local CLI (`capital-os tool call <tool_name>`).

## Adapter Overview

### HTTP Adapter
- Endpoint: `POST /tools/{tool_name}`
- Requires `x-capital-auth-token` and `x-correlation-id` (or `correlation_id` in body) headers.
- Returns JSON with HTTP status codes.

### CLI Adapter (Trusted Local Channel)
- Command: `capital-os tool call <tool_name> --json '<payload>'`
- No auth token required — CLI is a trusted local operator channel.
- All schema validation, event logging, and DB invariants are preserved.
- Installs as a console script: `pip install -e .` or `pipx install .`
- Success: canonical JSON payload on stdout, exit code `0`.
- Failure: structured error JSON on stderr, exit code `1`.

#### CLI Quick Reference
```bash
# List available tools
capital-os tool list

# Show tool schema
capital-os tool schema <tool_name>

# Call a tool with inline JSON
capital-os tool call <tool_name> --json '{"correlation_id":"local-001"}'

# Call a tool with a JSON file
capital-os tool call <tool_name> --json @payload.json

# Call a tool from stdin
echo '{"correlation_id":"local-002"}' | capital-os tool call <tool_name>

# Use a specific database
capital-os tool call <tool_name> --json '{}' --db-path /path/to/capital_os.db
```

## Common Contract Notes
- Input validation is done with Pydantic schemas in `src/capital_os/schemas/tools.py`.
- Authentication is required via `x-capital-auth-token` header for all tool calls.
- Authorization is capability-based and config-driven (`src/capital_os/config.py`), defaulting to deny on unmapped tools.
- `correlation_id` is mandatory for all tool calls and validated at API boundary before dispatch.
- Request hash: `input_hash = payload_hash(request_payload)`.
- Response hash: `output_hash = payload_hash(response_payload_without_output_hash)` for write tools and posture tool.
- Event logging target table: `event_log`.
- Validation failures return HTTP `422` with:
  - `detail.error = "validation_error"`
  - `detail.details = [pydantic errors]`

## `create_account`
- Handler: `src/capital_os/tools/create_account.py`
- Domain service: `src/capital_os/domain/accounts/service.py::create_account_entry`
- Input schema: `CreateAccountIn`
- Output schema: `CreateAccountOut`

### Behavior
- Creates a new account in the chart of accounts.
- Required fields: `code` (unique, 1-64 chars), `name` (1-256 chars), `account_type` (one of: `asset`, `liability`, `equity`, `income`, `expense`).
- Optional fields: `parent_account_id`, `entity_id` (defaults to `entity-default`), `metadata` (JSON object, defaults to `{}`).
- Validates `parent_account_id` exists before insert (returns 400 if not found).
- Validates `entity_id` exists before insert (returns 400 if not found).
- Rejects duplicate `code` values (returns 400).
- Rejects account hierarchy cycles via DB trigger (returns 400).
- Forbids unknown payload keys (`extra="forbid"`).
- Returns `status = "committed"` with `account_id` and `output_hash` on success.
- Logs event in same transaction (fail-closed).
- Capability: `tools:write`.

### CLI Invocation (Local Trusted Channel)
```bash
# Inline JSON
capital-os tool call create_account --json '{
  "code": "1100",
  "name": "Cash",
  "account_type": "asset",
  "correlation_id": "local-001"
}'

# From file
capital-os tool call create_account --json @create_account.json

# With explicit DB path
capital-os tool call create_account \
  --json '{"code":"1100","name":"Cash","account_type":"asset","correlation_id":"local-001"}' \
  --db-path /path/to/capital_os.db
```

## `update_account_metadata`
- Handler: `src/capital_os/tools/update_account_metadata.py`
- Domain service: `src/capital_os/domain/accounts/service.py::update_account_metadata`
- Input schema: `UpdateAccountMetadataIn`
- Output schema: `UpdateAccountMetadataOut`

### Behavior
- Updates account metadata using JSON merge-patch (RFC 7396) semantics.
- Required fields: `account_id`, `metadata` (JSON object), `correlation_id`.
- Merge-patch semantics:
  - Provided keys overwrite existing values.
  - Keys set to `null` are removed from metadata.
  - Unmentioned keys are preserved.
  - Nested objects are replaced wholesale (not deep-merged).
- Validates `account_id` exists (returns 400 if not found).
- Forbids unknown payload keys (`extra="forbid"`).
- Returns full merged `metadata`, `account_id`, `status = "committed"`, `correlation_id`, and `output_hash` on success.
- Logs event in same transaction (fail-closed).
- Capability: `tools:write`.

## `record_transaction_bundle`
- Handler: `src/capital_os/tools/record_transaction_bundle.py`
- Domain service: `src/capital_os/domain/ledger/service.py::record_transaction_bundle`
- Input schema: `RecordTransactionBundleIn`
- Output schema: `RecordTransactionBundleOut`

### Behavior
- Enforces all postings use `USD`.
- Enforces balanced postings (`sum(amount) == 0` after 4dp normalization).
- Uses idempotency key `(source_system, external_id)`.
- Supports optional `entity_id` (defaults to `entity-default`).
- Supports policy dimensions in request payload:
  - `transaction_category`
  - `risk_band`
- Supports period-control fields:
  - `is_adjusting_entry`, `adjusting_reason_code`
  - `override_period_lock`, `override_reason`
- Writes transaction + postings in one DB transaction.
- Persists canonical response payload and output hash for replay.
- Enforces expanded approval policy rules (threshold + category/entity/velocity/risk-band/tool matching).
- Enforces closed/locked period constraints prior to mutation.
- Returns:
  - `status = "committed"` on first commit.
  - `status = "idempotent-replay"` on duplicate key replay.
  - `status = "proposed"` for above-threshold requests (no ledger mutation).

### CLI Invocation (Local Trusted Channel)
```bash
capital-os tool call record_transaction_bundle --json '{
  "source_system": "example",
  "external_id": "tx-001",
  "date": "2026-01-01T00:00:00Z",
  "description": "Opening balance",
  "postings": [
    {"account_id": "<asset-account-id>", "amount": "100.00", "currency": "USD"},
    {"account_id": "<equity-account-id>", "amount": "-100.00", "currency": "USD"}
  ],
  "correlation_id": "local-001"
}'
```

## `record_balance_snapshot`
- Handler: `src/capital_os/tools/record_balance_snapshot.py`
- Domain service: `src/capital_os/domain/ledger/service.py::record_balance_snapshot`
- Input schema: `RecordBalanceSnapshotIn`
- Output schema: `RecordBalanceSnapshotOut`

### Behavior
- Upserts by unique `(account_id, snapshot_date)`.
- Supports optional `entity_id` (defaults to `entity-default`).
- Returns:
  - `status = "recorded"` on first insert.
  - `status = "updated"` on existing snapshot update.
- Logs event in same transaction.

## `create_or_update_obligation`
- Handler: `src/capital_os/tools/create_or_update_obligation.py`
- Domain service: `src/capital_os/domain/ledger/service.py::create_or_update_obligation`
- Input schema: `CreateOrUpdateObligationIn`
- Output schema: `CreateOrUpdateObligationOut`

### Behavior
- Upserts by unique `(source_system, name, account_id)`.
- Supports optional `entity_id` (defaults to `entity-default`).
- Returns:
  - `status = "created"` on first insert.
  - `status = "updated"` on existing obligation update.
- Reactivates obligation (`active = 1`) on update path.
- Logs event in same transaction.

## `compute_capital_posture`
- Handler: `src/capital_os/tools/compute_capital_posture.py`
- Engine: `src/capital_os/domain/posture/engine.py`
- Input schema: `ComputeCapitalPostureIn`
- Output schema: `ComputeCapitalPostureOut`

### Behavior
- Non-mutating calculation tool for posture metrics and risk band.
- Produces deterministic explanation payload sections:
  - `contributing_balances`
  - `reserve_assumptions`
- Persists event log entries for successful calls.

## `compute_consolidated_posture`
- Handler: `src/capital_os/tools/compute_consolidated_posture.py`
- Domain service: `src/capital_os/domain/posture/consolidation.py`
- Input schema: `ComputeConsolidatedPostureIn`
- Output schema: `ComputeConsolidatedPostureOut`

### Behavior
- Non-mutating consolidation tool across selected `entity_ids`.
- Requires deterministic per-entity posture inputs for every selected entity.
- Enforces inter-entity transfer paired semantics:
  - exactly two legs per `transfer_id`
  - one inbound and one outbound leg
  - mirrored entity/counterparty IDs
  - identical transfer amounts
- Computes transfer-neutral per-entity liquidity contributions and consolidated posture metrics.
- Returns deterministic entity ordering (`entity_ids` sorted) and stable `output_hash`.
- Emits event logs for success and validation failures.

## `simulate_spend`
- Handler: `src/capital_os/tools/simulate_spend.py`
- Engine: `src/capital_os/domain/simulation/engine.py`
- Input schema: `SimulateSpendIn`
- Output schema: `SimulateSpendOut`

### Behavior
- Non-mutating projection tool for one-time and recurring spend scenarios.
- Validates branch-specific fields (`one_time` requires `spend_date`, `recurring` requires `start_date`).
- Returns deterministic period projections with normalized monetary fields.
- Produces deterministic `output_hash` over canonical response payload.
- Persists event log entries for successful calls.

## `analyze_debt`
- Handler: `src/capital_os/tools/analyze_debt.py`
- Engine: `src/capital_os/domain/debt/engine.py`
- Input schema: `AnalyzeDebtIn`
- Output schema: `AnalyzeDebtOut`

### Behavior
- Non-mutating debt prioritization tool with deterministic ranking.
- Supports optional sensitivity branch via `optional_payoff_amount`.
- Returns per-liability score explanations:
  - `annual_interest_cost`
  - `cashflow_pressure`
  - `payoff_readiness`
- Applies deterministic tie-break ordering for equal score scenarios.
- Rejects secret-like liability identifiers and forbids unknown payload keys.
- Produces deterministic `output_hash` over canonical response payload.
- Persists event log entries for successful calls.

## `approve_proposed_transaction`
- Handler: `src/capital_os/tools/approve_proposed_transaction.py`
- Domain service: `src/capital_os/domain/approval/service.py::approve_proposed_transaction`
- Input schema: `ApproveProposedTransactionIn`
- Output schema: `ApproveProposedTransactionOut`

### Behavior
- Approves previously proposed `record_transaction_bundle` requests.
- Supports optional multi-party approvals using `approver_id` when proposal requires quorum.
- Returns intermediate `status = "proposed"` until required approvals are satisfied.
- Commits exactly one canonical transaction under concurrent duplicate approval attempts.
- Returns deterministic replay-safe canonical result for duplicate retries.
- Logs success and validation failures.

## `reject_proposed_transaction`
- Handler: `src/capital_os/tools/reject_proposed_transaction.py`
- Domain service: `src/capital_os/domain/approval/service.py::reject_proposed_transaction`
- Input schema: `RejectProposedTransactionIn`
- Output schema: `RejectProposedTransactionOut`

### Behavior
- Rejects previously proposed `record_transaction_bundle` requests without mutating ledger transactions/postings.
- Supports deterministic idempotent replay behavior on duplicate reject attempts.
- Logs success and validation failures.

## `close_period`
- Handler: `src/capital_os/tools/close_period.py`
- Domain service: `src/capital_os/domain/periods/service.py::close_period`
- Input schema: `ClosePeriodIn`
- Output schema: `ClosePeriodOut`

### Behavior
- Closes an accounting period by `period_key` and `entity_id`.
- Idempotent:
  - first close returns `status = "closed"`
  - repeat close returns `status = "already_closed"`
  - close after lock returns `status = "already_locked"`
- Emits event logs for success and validation failures.

## `lock_period`
- Handler: `src/capital_os/tools/lock_period.py`
- Domain service: `src/capital_os/domain/periods/service.py::lock_period`
- Input schema: `LockPeriodIn`
- Output schema: `LockPeriodOut`

### Behavior
- Locks an accounting period by `period_key` and `entity_id`.
- Idempotent:
  - first lock returns `status = "locked"`
  - repeat lock returns `status = "already_locked"`
- Locked periods block back-dated writes unless explicit override path is used and policy approval conditions are met.
- Emits event logs for success and validation failures.

## `list_accounts`
- Handler: `src/capital_os/tools/list_accounts.py`
- Domain service: `src/capital_os/domain/query/service.py::query_accounts_page`
- Input schema: `ListAccountsIn`
- Output schema: `ListAccountsOut`

### Behavior
- Deterministic keyset pagination ordered by `(code, account_id)`.
- Cursor is canonical opaque payload over `{v, code, account_id}`.
- Malformed cursor returns deterministic `422` validation error.
- Emits event logs for success and validation failures.

### CLI Invocation (Local Trusted Channel)
```bash
# List all accounts
capital-os tool call list_accounts --json '{"correlation_id": "local-001"}'

# With pagination
capital-os tool call list_accounts --json '{"correlation_id": "local-002", "limit": 20}'

# Pipe to jq for formatting
capital-os tool call list_accounts --json '{"correlation_id": "local-003"}' | jq .accounts
```

## `get_account_tree`
- Handler: `src/capital_os/tools/get_account_tree.py`
- Domain service: `src/capital_os/domain/query/service.py::query_account_tree`
- Input schema: `GetAccountTreeIn`
- Output schema: `GetAccountTreeOut`

### Behavior
- Returns deterministic account hierarchy tree with children sorted by `(code, account_id)`.
- Supports optional subtree root via `root_account_id`.
- Emits event logs for success and validation failures.

## `get_account_balances`
- Handler: `src/capital_os/tools/get_account_balances.py`
- Domain service: `src/capital_os/domain/query/service.py::query_account_balances`
- Input schema: `GetAccountBalancesIn`
- Output schema: `GetAccountBalancesOut`

### Behavior
- Returns deterministic per-account balances as-of date in `(code, account_id)` order.
- Supports `source_policy` (optional; defaults to configured `CAPITAL_OS_BALANCE_SOURCE_POLICY`):
  - `ledger_only`: summed ledger postings at or before `as_of_date`
  - `snapshot_only`: latest snapshot at or before `as_of_date` (`source_used = none` if missing)
  - `best_available`: snapshot when present, otherwise ledger
- Includes `ledger_balance`, `snapshot_balance`, selected `balance`, and `source_used`.
- Emits event logs for success and validation failures.

## `list_transactions`
- Handler: `src/capital_os/tools/list_transactions.py`
- Domain service: `src/capital_os/domain/query/service.py::query_transactions_page`
- Input schema: `ListTransactionsIn`
- Output schema: `ListTransactionsOut`

### Behavior
- Deterministic keyset pagination ordered by `(transaction_date DESC, transaction_id ASC)`.
- Cursor is canonical opaque payload over `{v, transaction_date, transaction_id}`.
- Emits event logs for success and validation failures.

## `get_transaction_by_external_id`
- Handler: `src/capital_os/tools/get_transaction_by_external_id.py`
- Domain service: `src/capital_os/domain/query/service.py::query_transaction_by_external_id`
- Input schema: `GetTransactionByExternalIdIn`
- Output schema: `GetTransactionByExternalIdOut`

### Behavior
- Deterministically resolves transaction by `(source_system, external_id)`.
- Includes postings sorted by `(account_code, posting_id)`.
- Emits event logs for success and validation failures.

## `list_obligations`
- Handler: `src/capital_os/tools/list_obligations.py`
- Domain service: `src/capital_os/domain/query/service.py::query_obligations_page`
- Input schema: `ListObligationsIn`
- Output schema: `ListObligationsOut`

### Behavior
- Deterministic keyset pagination ordered by `(next_due_date ASC, obligation_id ASC)`.
- Supports `active_only` filter with deterministic output.
- Cursor is canonical opaque payload over `{v, next_due_date, obligation_id}`.
- Emits event logs for success and validation failures.

## `list_proposals`
- Handler: `src/capital_os/tools/list_proposals.py`
- Domain service: `src/capital_os/domain/query/service.py::query_proposals_page`
- Input schema: `ListProposalsIn`
- Output schema: `ListProposalsOut`

### Behavior
- Deterministic keyset pagination ordered by `(created_at DESC, proposal_id ASC)`.
- Supports optional `status` filter.
- Cursor is canonical opaque payload over `{v, created_at, proposal_id}`.
- Emits event logs for success and validation failures.

## `get_proposal`
- Handler: `src/capital_os/tools/get_proposal.py`
- Domain service: `src/capital_os/domain/query/service.py::query_proposal`
- Input schema: `GetProposalIn`
- Output schema: `GetProposalOut`

### Behavior
- Returns proposal details plus decisions timeline ordered by `(created_at, decision_id)`.
- Emits event logs for success and validation failures.

## `get_config`
- Handler: `src/capital_os/tools/get_config.py`
- Domain service: `src/capital_os/domain/query/service.py::query_config`
- Input schema: `GetConfigIn`
- Output schema: `GetConfigOut`

### Behavior
- Returns runtime config snapshot and deterministic policy-rule list.
- Emits event logs for success and validation failures.

## `propose_config_change`
- Handler: `src/capital_os/tools/propose_config_change.py`
- Input schema: `ProposeConfigChangeIn`
- Output schema: `ProposeConfigChangeOut`

### Behavior
- Creates deterministic config-change proposal record using approval tables.
- Idempotency scope is `(tool_name='propose_config_change', source_system, external_id)`.
- Does not directly mutate runtime configuration.
- Emits event logs for success and validation failures.

## `approve_config_change`
- Handler: `src/capital_os/tools/approve_config_change.py`
- Input schema: `ApproveConfigChangeIn`
- Output schema: `ApproveConfigChangeOut`

### Behavior
- Approves config-change proposals and persists decision trail.
- Returns deterministic statuses: `applied`, `already_applied`, or `rejected`.
- Emits event logs for success and validation failures.

## `reconcile_account`
- Handler: `src/capital_os/tools/reconcile_account.py`
- Domain service: `src/capital_os/domain/reconciliation/service.py::reconcile_account`
- Input schema: `ReconcileAccountIn`
- Output schema: `ReconcileAccountOut`

### Behavior
- Non-mutating reconciliation tool for a single account as-of date.
- Compares `ledger_balance` vs latest `snapshot_balance` and returns `delta = snapshot_balance - ledger_balance`.
- `method` controls truth selection and suggestion behavior:
  - `ledger_only`: no adjustment suggestion.
  - `snapshot_only`: proposes reconciliation adjustment bundle when snapshot exists and `delta != 0`.
  - `best_available`: behaves like snapshot when snapshot exists, otherwise ledger.
- Suggested adjustments are always proposal-only (`auto_commit = false`) and never write ledger rows.
- Emits event logs for success and validation failures.

## Error Semantics
- Unknown tool: HTTP `404`, `{"error":"unknown_tool","tool":<tool_name>}`.
- Missing/invalid auth token: HTTP `401`, `{"error":"authentication_required"}`.
- Capability denied: HTTP `403`, `{"error":"forbidden"}`.
- Validation failure: HTTP `422` deterministic detail payload, with event logging attempt.
- Validation payloads are sanitized to avoid echoing raw input values.
- Tool execution failure: HTTP `400`, `{"error":"tool_execution_error","message":...}`.
- Health failure: HTTP `503` from `/health`.

## Observability Fields Logged
Logged by `src/capital_os/observability/event_log.py`:
- `tool_name`
- `correlation_id`
- `input_hash`
- `output_hash`
- `event_timestamp`
- `duration_ms`
- `status`
- `error_code` (optional)
- `error_message` (optional)
- `actor_id` (optional)
- `authn_method` (optional)
- `authorization_result` (optional)
- `violation_code` (optional)
