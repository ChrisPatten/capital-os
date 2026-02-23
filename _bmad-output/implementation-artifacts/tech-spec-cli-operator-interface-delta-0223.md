---
title: 'CLI Operator Interface Delta (0223)'
slug: 'cli-operator-interface-delta-0223'
created: '2026-02-23T00:00:00Z'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Python'
  - 'Typer (Click-based CLI)'
  - 'FastAPI'
  - 'SQLite (file-backed, WAL)'
  - 'Pytest'
---

# Tech-Spec: CLI Operator Interface Delta

## Overview

This delta adds a first-class local CLI command (`capital-os`) as a trusted adapter over the existing Capital OS tool runtime so operators and local agents can call tools without running the HTTP server.

The CLI is an additional transport, not a separate logic stack. All core tool behavior (schema validation, deterministic hashing, transaction handling, event logging, and domain invariants) remains centralized in a shared runtime execution path.

## Architectural Decision Summary

- Add a **trusted local CLI adapter** that bypasses auth/authz checks only.
- Refactor the API adapter to call a **shared tool execution entrypoint**.
- Package a real `capital-os` console script via `pyproject.toml`.
- Use a CLI framework with high-quality help and shell completion support (`Typer`).
- Preserve identical canonical tool outputs and `output_hash` behavior across adapters.
- Keep CLI local-only by construction in this delta (no remote proxy mode).

## Trusted CLI Channel Rules

### Security / Boundary Semantics
- CLI is a **trusted local operator channel**.
- CLI **does not** require auth token or capability checks.
- CLI **does** enforce:
  - request schema validation
  - deterministic input/output hashing
  - DB transaction boundaries
  - ledger invariants and append-only protections
  - event logging requirements (including fail-closed write behavior)

### Execution Context Injection
CLI adapter injects a fixed runtime context for observability and traceability, for example:
- `actor_id = "local-cli"`
- `authn_method = "trusted_cli"`
- `authorization_result = "bypassed_trusted_channel"`

These fields must be distinguishable from HTTP-authenticated calls in the event log.

## Architecture Changes

### Shared Runtime Execution Path (New)
- Add a shared executor module (example):
  - `src/capital_os/runtime/execute_tool.py`
- Responsibilities:
  - canonical tool lookup / dispatch
  - request schema validation invocation
  - correlation/context enforcement at shared boundary (except auth-specific HTTP concerns)
  - shared error mapping to internal result envelope
  - deterministic input/output hashing hooks
  - event logging orchestration and write fail-closed semantics

### API Adapter (Refactor)
- `src/capital_os/api/app.py` becomes an HTTP transport adapter over the shared executor.
- API retains:
  - header authn parsing
  - capability authz enforcement
  - HTTP status code mapping and response envelopes
- API delegates tool semantics and execution to shared runtime entrypoint.

### CLI Adapter (New)
- Add CLI package modules (example):
  - `src/capital_os/cli/main.py`
  - `src/capital_os/cli/tool.py`
  - `src/capital_os/cli/server.py`
  - `src/capital_os/cli/context.py`
- CLI delegates to shared runtime entrypoint with trusted local execution context.
- CLI handles shell UX, argument parsing, and output formatting only.

## CLI Command Surface (Initial)

### Core Commands
- `capital-os health`
  - Local mode health checks DB/runtime readiness without requiring HTTP server.
- `capital-os tool list`
  - Lists available tool names with short descriptions.
- `capital-os tool schema <tool_name>`
  - Displays input/output schema and basic examples.
- `capital-os tool call <tool_name>`
  - Invokes a tool locally using JSON payload input.
- `capital-os serve`
  - Starts existing HTTP runtime path (operator convenience wrapper).

### Input / Output Design
- Tool calls accept payloads via:
  - `--json @payload.json`
  - `--json '{"..."}'`
  - `--stdin` (or stdin auto-detect when piped)
- Local-mode commands support explicit database selection via `--db-path` (with env/config fallback if omitted).
- Success:
  - canonical JSON to stdout
  - exit code `0`
- Failures:
  - structured error JSON to stderr
  - non-zero exit code

### Shell UX Quality Targets
- Excellent generated `--help` text for all commands
- Embedded examples in help output for common commands
- Completion support for `bash`, `zsh`, `fish`
- Stable flag naming (`--db-path`, `--config`, `--json`, `--output`, etc.)

### Local Database Selection Requirements
- `--db-path` is supported as a global option or consistently available on all local-mode commands (`health`, `tool list`, `tool schema`, `tool call`).
- When `--db-path` is provided, the CLI uses that SQLite file for all local execution.
- Missing/unopenable DB path returns structured error output on stderr and non-zero exit code.

## Packaging and Installation Strategy

### Python Packaging Change
Add a console script entry in `pyproject.toml`:

- `[project.scripts]`
- `capital-os = capital_os.cli.main:app` (or `:main`)

### Supported Install Paths (Initial)
- Dev: `pip install -e .`
- Dev (alt): `uv pip install -e .`
- Local operator install: `pipx install .`
- CI/runtime artifact install: wheel/sdist install from build output

### Fallback
- `python -m capital_os.cli.main` may remain available for debugging, but is not the primary documented operator path.

## Determinism and Parity Requirements (Delta)

- Identical stored state + identical input payload must produce identical canonical tool response payload and `output_hash` across:
  - HTTP adapter
  - trusted local CLI adapter
- Differences allowed only in transport-level concerns:
  - HTTP status code / headers
  - CLI stderr/stdout routing and exit codes

## Testing Plan

### Integration / Parity
- CLI tool invocation happy path for representative write and read tools.
- CLI validation failure shape is deterministic and machine-readable.
- CLI trusted context fields are persisted in event log.
- CLI/HTTP adapter parity tests assert canonical response equivalence and `output_hash` equality.
- CLI local execution honors `--db-path` selection for isolated test databases.

### Shell UX
- Smoke tests for `--help` on root and nested commands.
- Completion generation smoke checks (`--show-completion` / `--install-completion` if framework supports).

### Packaging
- Editable install smoke (`pip install -e .`) produces `capital-os` command.
- Optional `pipx install .` smoke in local/manual validation docs.

## Migration / Schema Impact

- No migration required for core CLI support.
- Existing event log schema already supports channel-distinguishing context fields (`actor_id`, `authn_method`, `authorization_result`).

## Backlog Mapping

- Epic 15: CLI Operator Interface and Trusted Local Adapter
  - Story 15.1: Shared Tool Executor and Adapter Refactor
  - Story 15.2: Packaged CLI Command, Command Surface, and Shell Integration
  - Story 15.3: CLI/HTTP Parity Tests and Operator Documentation
