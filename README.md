# Capital OS

Capital OS is a deterministic, auditable financial truth layer built around a double-entry ledger and schema-validated tool APIs for agent use.

## Current Status (2026-02-14)
- Core ledger foundation is implemented: accounts, balanced transaction bundles, idempotency, balance snapshots, obligations, and event logging.
- Capital posture tooling is implemented (`compute_capital_posture`).
- Spend simulation tooling is implemented (`simulate_spend`) with contract, logging, and latency guardrail coverage.
- Remaining roadmap backlog starts at Epic 3 (debt analysis, approval-gated writes, CI hardening).

## Tech Stack
- Python 3.11+
- FastAPI (`GET /health`, `POST /tools/{tool_name}`)
- SQLite (file-backed, WAL mode)
- Pytest (unit/integration/replay/security/perf)

## Repository Layout
```text
src/capital_os/
  api/             # FastAPI transport
  tools/           # Tool handlers and schema boundary
  domain/          # Accounts, ledger, and posture domain logic
  db/              # SQLite connection and transaction helpers
  observability/   # Event log + deterministic hashing
  schemas/         # Pydantic request/response contracts
migrations/        # Numbered schema migrations + rollback scripts
tests/             # Unit/integration/replay/security/perf coverage
docs/              # Project and agent documentation
```

## Quickstart
1. Install dependencies:
```bash
pip install -e ".[dev]"
```
2. Set database URL (optional, default shown):
```bash
export CAPITAL_OS_DB_URL=sqlite:///./data/capital_os.db
```
3. Run the API:
```bash
uvicorn capital_os.main:app --reload
```
4. Run tests:
```bash
pytest
```

## API Surface
- Health:
  - `GET /health`
- Tool endpoint:
  - `POST /tools/{tool_name}`
- Registered tools:
  - `record_transaction_bundle`
  - `record_balance_snapshot`
  - `create_or_update_obligation`
  - `compute_capital_posture`
  - `simulate_spend`

## Example Tool Call
```bash
curl -sS -X POST http://127.0.0.1:8000/tools/record_transaction_bundle \
  -H "content-type: application/json" \
  -d '{
    "source_system":"example",
    "external_id":"tx-001",
    "date":"2026-01-01T00:00:00Z",
    "description":"Opening balance",
    "postings":[
      {"account_id":"<asset-account-id>","amount":"100.00","currency":"USD"},
      {"account_id":"<equity-account-id>","amount":"-100.00","currency":"USD"}
    ],
    "correlation_id":"corr-001"
  }'
```

## Core Guarantees
- Balanced transaction bundles are enforced before commit.
- Idempotency key is `(source_system, external_id)` for transaction recording.
- Monetary values are normalized to 4 decimal places with round-half-even.
- Tool input/output hashing is deterministic.
- Tool invocations are event-logged (success and validation failures).
- Append-only protections exist on transaction, posting, and event-log history.

## Documentation Index
- `docs/README.md`
- `docs/current-state.md`
- `docs/tool-reference.md`
- `docs/data-model.md`
- `docs/testing-matrix.md`
- `docs/development-workflow.md`
- `docs/agent-playbooks/README.md`
- `docs/backlog-phase1-prd-closure.md`

## Planning and Backlog Source of Truth
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Story briefs: `_bmad-output/implementation-artifacts/*.md`
- Epic planning: `_bmad-output/planning-artifacts/epic-*.md`
- PRD baseline: `initial_prd.md`
