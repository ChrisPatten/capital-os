# Tool Reference

As of 2026-02-14, the service exposes `POST /tools/{tool_name}` in `src/capital_os/api/app.py`.

## Common Contract Notes
- Input validation is done with Pydantic schemas in `src/capital_os/schemas/tools.py`.
- Request hash: `input_hash = payload_hash(request_payload)`.
- Response hash: `output_hash = payload_hash(response_payload_without_output_hash)` for write tools and posture tool.
- Event logging target table: `event_log`.
- Validation failures return HTTP `422` with:
  - `detail.error = "validation_error"`
  - `detail.details = [pydantic errors]`

## `record_transaction_bundle`
- Handler: `src/capital_os/tools/record_transaction_bundle.py`
- Domain service: `src/capital_os/domain/ledger/service.py::record_transaction_bundle`
- Input schema: `RecordTransactionBundleIn`
- Output schema: `RecordTransactionBundleOut`

### Behavior
- Enforces all postings use `USD`.
- Enforces balanced postings (`sum(amount) == 0` after 4dp normalization).
- Uses idempotency key `(source_system, external_id)`.
- Writes transaction + postings in one DB transaction.
- Persists canonical response payload and output hash for replay.
- Returns:
  - `status = "committed"` on first commit.
  - `status = "idempotent-replay"` on duplicate key replay.

## `record_balance_snapshot`
- Handler: `src/capital_os/tools/record_balance_snapshot.py`
- Domain service: `src/capital_os/domain/ledger/service.py::record_balance_snapshot`
- Input schema: `RecordBalanceSnapshotIn`
- Output schema: `RecordBalanceSnapshotOut`

### Behavior
- Upserts by unique `(account_id, snapshot_date)`.
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

## Error Semantics
- Unknown tool: HTTP `404`, `{"error":"unknown_tool","tool":<tool_name>}`.
- Validation failure: HTTP `422` deterministic detail payload, with event logging attempt.
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
