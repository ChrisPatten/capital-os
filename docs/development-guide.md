# Development Guide

## Prerequisites

- Python `>=3.11`
- `pip` (or `uv`)
- SQLite-compatible filesystem path for DB file

## Setup

1. Install dependencies:

```bash
pip install -e ".[dev]"
```

2. Set DB URL (optional default shown):

```bash
export CAPITAL_OS_DB_URL=sqlite:///./data/capital_os.db
```

3. Apply migrations and seed baseline data:

```bash
make init
```

## Run Modes

### API Server (Uvicorn)

```bash
uvicorn capital_os.main:app --reload
```

### Managed Runtime (Make)

```bash
make run
make health
make stop
```

### Trusted CLI Channel

```bash
capital-os health
capital-os tool list
capital-os tool call list_accounts --json '{"correlation_id":"local-001"}'
```

## Testing

- Full test suite:

```bash
pytest
```

- Performance-focused tests:

```bash
pytest -m performance
```

- Migration cycle validation:

```bash
python3 scripts/check_migration_cycle.py
```

## Common Workflows

- Re-apply pending migrations: `python3 scripts/apply_migrations.py`
- Validate COA config: `python3 scripts/import_coa.py config/coa.yaml --validate-only`
- Deterministic smoke flow: `make mvp-smoke`
