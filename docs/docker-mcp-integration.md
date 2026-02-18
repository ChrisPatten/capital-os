# Docker & MCP Integration

Last updated: 2026-02-18

Capital OS now provides a containerized **Model Context Protocol (MCP)** server that exposes all 25 financial tools via stdio JSON-RPC. This enables seamless integration with Claude Code, Claude Desktop, and other MCP clients.

## Overview

**Architecture:**
```
Claude Code (stdio)
    ↓
MCP Server (mcp/server.py) — JSON-RPC 2.0 protocol
    ↓
Capital OS HTTP API (http://127.0.0.1:8000)
    ↓
SQLite Database (mounted volume)
```

**Key features:**
- All 25 Capital OS tools exposed as MCP tools with full schema
- Automatic `correlation_id` injection (UUID per call)
- Clean stdio (logs → stderr, JSON-RPC → stdout)
- Persistent data via Docker volume mounting
- Dev and production auth token support

## Quick Start

### Build the container
```bash
docker build -t capital-os-mcp .
```

### Run locally (smoke test)
```bash
docker run -i --rm \
  -v capital-os-data:/app/data \
  capital-os-mcp:latest
```

The container will:
1. Auto-initialize the database (if missing)
2. Start the Capital OS HTTP backend
3. Wait for health check
4. Start the MCP server on stdio

### Use with Claude Desktop

1. **Update `.mcp.json`** (already configured):
```json
{
  "mcpServers": {
    "capital-os": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "capital-os-data:/app/data",
        "capital-os-mcp:latest"
      ]
    }
  }
}
```

2. **Restart Claude Desktop** to pick up the MCP server.

3. **In Claude Desktop**, use Capital OS tools:
```
List all accounts:
<use the list_accounts tool>

Create a transaction:
<use the record_transaction_bundle tool>
```

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CAPITAL_OS_BASE_URL` | `http://127.0.0.1:8000` | Backend API endpoint |
| `CAPITAL_OS_AUTH_TOKEN` | `dev-admin-token` | Auth token for backend |
| `CAPITAL_OS_DB_URL` | `sqlite:///./data/capital_os.db` | Database connection string |

**Example with custom auth token:**
```bash
docker run -i --rm \
  -v capital-os-data:/app/data \
  -e CAPITAL_OS_AUTH_TOKEN=my-custom-token \
  capital-os-mcp:latest
```

### Persistent Data

**Option 1: Named volume** (recommended for dev)
```bash
docker run -i --rm \
  -v capital-os-data:/app/data \
  capital-os-mcp:latest
```

**Option 2: Host directory** (recommended for production/migration)
```bash
docker run -i --rm \
  -v /path/to/existing/data:/app/data \
  capital-os-mcp:latest
```

**Option 3: Docker compose**
```yaml
services:
  capital-os-mcp:
    build: .
    image: capital-os-mcp:latest
    stdin_open: true
    volumes:
      - capital-os-data:/app/data  # or /path/to/existing/data:/app/data
    environment:
      - CAPITAL_OS_AUTH_TOKEN=${CAPITAL_OS_AUTH_TOKEN:-dev-admin-token}

volumes:
  capital-os-data:
```

Run with:
```bash
docker-compose up
```

## Using Existing Database

To use an existing SQLite database file:

```bash
# Assuming your database is at /path/to/capital_os.db
docker run -i --rm \
  -v /path/to/capital_os.db:/app/data/capital_os.db \
  capital-os-mcp:latest
```

The container **skips initialization** if the database already exists, preserving your data.

## Tools Reference

All 25 Capital OS tools are exposed as MCP tools. Each tool maps directly to the HTTP API:

### Account Management
- `create_account` — Create account
- `update_account_metadata` — Update account metadata
- `list_accounts` — List accounts (paginated)
- `get_account_tree` — Get account hierarchy
- `get_account_balances` — Get all account balances

### Transactions
- `record_transaction_bundle` — Record balanced transaction (idempotent)
- `list_transactions` — List transactions (paginated)
- `get_transaction_by_external_id` — Look up by source system + ID

### Obligations & Snapshots
- `record_balance_snapshot` — Record external balance snapshot
- `reconcile_account` — Reconcile ledger vs snapshot
- `create_or_update_obligation` — Create/update recurring obligation
- `list_obligations` — List obligations (paginated)

### Capital Analysis
- `compute_capital_posture` — Compute entity posture + risk band
- `compute_consolidated_posture` — Consolidate across entities
- `simulate_spend` — Project liquidity under spend plan
- `analyze_debt` — Rank liabilities by payoff priority

### Approvals & Config
- `list_proposals` — List approval proposals (paginated)
- `get_proposal` — Get proposal details
- `approve_proposed_transaction` — Approve transaction proposal
- `reject_proposed_transaction` — Reject transaction proposal
- `get_config` — Get runtime config + policy rules
- `propose_config_change` — Propose config change
- `approve_config_change` — Approve config change

### Period Management
- `close_period` — Close accounting period
- `lock_period` — Lock closed period

**Tool schema auto-generation:** Schemas are generated from Pydantic models in `src/capital_os/schemas/tools.py` with `correlation_id` automatically stripped (auto-injected by MCP server).

## Troubleshooting

### "INFO:" messages in Claude Desktop
**Problem:** uvicorn logs polluting JSON-RPC stream.

**Fix:** Already fixed in `mcp/entrypoint.sh` — uvicorn logs are redirected to stderr.

**If issue persists, rebuild:**
```bash
docker build -t capital-os-mcp . --no-cache
```

### MCP connection fails
**Check 1:** Container is running
```bash
docker ps | grep capital-os-mcp
```

**Check 2:** Backend is healthy
```bash
docker exec <container-id> curl -sf http://127.0.0.1:8000/health
```

**Check 3:** MCP server process is running
```bash
docker logs <container-id>
```

### Database not persisting
**Problem:** Data lost between container restarts.

**Fix:** Use volume mount correctly:
```bash
# WRONG - data in container ephemeral filesystem
docker run -i --rm capital-os-mcp:latest

# CORRECT - data in named volume
docker run -i --rm -v capital-os-data:/app/data capital-os-mcp:latest

# CORRECT - data in host directory
docker run -i --rm -v /path/to/data:/app/data capital-os-mcp:latest
```

### Custom token not working
**Problem:** 401 errors from API.

**Fix:** Ensure token is passed to container and backend supports it:
```bash
# Container-side
docker run -i --rm \
  -v capital-os-data:/app/data \
  -e CAPITAL_OS_AUTH_TOKEN=my-token \
  capital-os-mcp:latest

# Verify backend config supports token
# (check CAPITAL_OS_AUTH_TOKENS_JSON in backend container)
```

## Development

### Running tests locally (not in container)
```bash
pytest tests/
pytest tests/unit/
pytest -k "mcp or docker"  # No MCP-specific unit tests yet (stdio protocol tested via integration)
```

### Building for CI/CD
```bash
# Without cache (always fresh)
docker build -t capital-os-mcp:latest . --no-cache

# With specific tag for release
docker build -t capital-os-mcp:v0.1.0 .
docker tag capital-os-mcp:v0.1.0 capital-os-mcp:latest
```

### Manual health check from outside container
```bash
# Start container in background
docker run -d --name capital-os-test -v capital-os-data:/app/data capital-os-mcp:latest

# Wait a few seconds
sleep 3

# Test health
curl http://127.0.0.1:8000/health  # Will fail (port not exposed)

# OR use docker exec
docker exec capital-os-test curl -sf http://127.0.0.1:8000/health

# Cleanup
docker stop capital-os-test && docker rm capital-os-test
```

## Architecture Details

### File Structure
```
mcp/
  entrypoint.sh      # Container init: DB setup, backend start, MCP server exec
  server.py          # MCP JSON-RPC 2.0 handler
  smoke_test.py      # Validation script (optional, for CI)

Dockerfile           # Multi-stage build (could be optimized)
docker-compose.yml   # Dev helper
.dockerignore        # Exclude .git, tests/, *.pyc, etc.
.mcp.json            # Claude Code/Desktop MCP config
```

### MCP Server (`mcp/server.py`)

**Key responsibilities:**
1. **Tool registration** — Imports all 25 Pydantic `*In` models from `capital_os.schemas.tools`
2. **Schema generation** — Calls `model_json_schema()` and strips `correlation_id` field
3. **Tool discovery** — Responds to `tools/list` with full schemas
4. **Tool dispatch** — Routes `tools/call` to backend HTTP API
5. **Auth injection** — Adds `x-capital-auth-token` header from env
6. **Correlation ID injection** — Auto-generates UUID per call
7. **Error handling** — Maps HTTP errors to MCP error responses

**Sample flow:**
```
Client → tools/list request
  ↓
server.py reads TOOLS registry
  ↓
Returns 25 tools + schemas (correlation_id stripped)
  ↓
Client → tools/call {name: "list_accounts", arguments: {...}}
  ↓
server.py injects correlation_id = uuid4()
  ↓
POST http://127.0.0.1:8000/tools/list_accounts
  Header: x-capital-auth-token: dev-admin-token
  Body: {...all arguments...}
  ↓
Backend validates + executes
  ↓
Response JSON → client
```

### Entrypoint (`mcp/entrypoint.sh`)

**Execution order:**
1. Check if DB exists at `$CAPITAL_OS_DB_PATH` (default `/app/data/capital_os.db`)
2. If missing:
   - Run `scripts/apply_migrations.py` (create schema)
   - Run `scripts/import_coa.py config/coa.yaml` (seed COA)
3. Start `uvicorn` in background, redirecting logs to stderr (`>&2`)
4. Wait for health check (curl loop, up to 15 seconds)
5. Execute MCP server in foreground on stdio

**Why logs → stderr?**
- MCP uses stdio for JSON-RPC protocol (must be clean)
- Application logs go to stderr (displayed by Claude Desktop, saved in docker logs)
- Prevents protocol parsing errors

## Integration Checklist

- [x] Dockerfile builds successfully
- [x] Container initializes DB
- [x] uvicorn starts and is healthy
- [x] MCP server accepts connections
- [x] All 25 tools available via `tools/list`
- [x] Tool calls work end-to-end
- [x] Logs separated (stdout clean, stderr logged)
- [x] Volume mounting preserves data
- [x] `.mcp.json` configures Claude Desktop
- [x] Auth token injection works
- [x] Correlation IDs auto-generated

## Next Steps

- [ ] Push image to container registry (Docker Hub / GCR / ECR)
- [ ] Add health check to docker-compose.yml
- [ ] Add resource limits (CPU, memory) to docker-compose.yml
- [ ] Multi-stage Dockerfile optimization
- [ ] CI/CD pipeline for image builds + tests
- [ ] Production deployment guide (K8s, Docker Swarm, etc.)
