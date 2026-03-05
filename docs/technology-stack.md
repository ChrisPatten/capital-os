# Technology Stack

## Core Runtime

| Category | Technology | Version | Justification |
| --- | --- | --- | --- |
| Language | Python | `>=3.11` | Declared in `pyproject.toml` and used across runtime, tooling, and tests. |
| API Framework | FastAPI | `>=0.116.0` | HTTP transport (`GET /health`, `POST /tools/{tool_name}`) in `src/capital_os/api/app.py`. |
| Validation | Pydantic | `>=2.11.0` | Tool contracts and request/response schemas in `src/capital_os/schemas/tools.py`. |
| Server | Uvicorn | `>=0.35.0` | ASGI runtime used in local and scripted run flows. |
| CLI | Typer | `>=0.15.0` | Trusted local operator channel (`capital-os` command). |
| Data Store | SQLite | file-backed + WAL | Canonical ledger store with `PRAGMA journal_mode = WAL` in DB session/migration code. |
| Config/Data | PyYAML | `>=6.0.2` | YAML config and chart-of-accounts support. |
| Test Framework | Pytest | `>=8.3.0` | Unit/integration/replay/security/perf test suites under `tests/`. |

## Package/Build

- Build backend: `setuptools.build_meta`
- Distribution metadata: `project.name = capital-os`, `version = 0.1.1`
- Entry point: `capital-os = capital_os.cli.main:app`

## Platform Signals

- Primary transport modes: HTTP API + trusted local CLI
- Persistence strategy: SQLite single-file DB with explicit migration chain and rollback SQL
- Determinism scaffolding: canonical hashing, correlation IDs, replay suites
