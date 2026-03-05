# Deployment Guide

## Runtime Model

- FastAPI application served by Uvicorn.
- SQLite file-backed datastore (WAL mode enabled in session layer).
- Optional containerized MCP mode via Docker.

## Required Runtime Configuration

- `CAPITAL_OS_DB_URL` (required for non-default database location)
- `CAPITAL_OS_AUTH_TOKENS_JSON` (optional auth token map override)
- `CAPITAL_OS_TOOL_CAPABILITIES_JSON` (optional capability map override)
- `CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT` (optional governance setting)

## Migration and Bootstrap Sequence

1. Apply schema migrations:

```bash
python3 scripts/apply_migrations.py
```

2. Seed chart of accounts (if needed):

```bash
python3 scripts/import_coa.py config/coa.yaml
```

3. Verify readiness:

```bash
curl -fsS http://127.0.0.1:8000/health
```

## Container Path

- Build image: `docker build -t capital-os-mcp .`
- Run MCP container: `docker run -i --rm -v capital-os-data:/app/data capital-os-mcp:latest`

## CI/CD Signals

- GitHub Actions pipeline: `.github/workflows/ci.yml`
- Migration forward/rollback validation script is present in `scripts/check_migration_cycle.py`.
