# Epic 15: CLI Operator Interface and Trusted Local Adapter

## Goal
Provide a first-class `capital-os` CLI command that can invoke Capital OS tools locally without running the HTTP server, while preserving the same validation, determinism, transaction, and audit guarantees as the API path.

## Why This Epic Exists
- Local operator and agent workflows currently depend on starting the FastAPI server for every interaction.
- `python -m ...` invocation patterns are awkward for shell automation, discoverability, and onboarding.
- Capital OS already has strong tool contracts and execution semantics that can be reused through an adapter model.
- A packaged CLI command enables better shell integration: `--help`, examples, tab completion, scripting-friendly JSON output, and stable exit codes.
- A trusted local CLI channel reduces operational friction while keeping ledger safety invariants intact.

## Scope Boundaries
- In scope:
  - Trusted local CLI adapter (`capital-os`) for tool invocation without HTTP server
  - Shared tool execution entrypoint used by both HTTP and CLI adapters
  - CLI command surface for `health`, tool listing/schema discovery, and tool calls
  - Packaged console script installation via `pyproject.toml`
  - Shell UX improvements: rich help, examples, tab completion, JSON/stdout discipline
  - Adapter parity tests (CLI vs HTTP canonical tool outputs/hashes for shared behavior)
  - Operator documentation for install, completion, and usage
- Out of scope:
  - Remote CLI execution mode (future option may proxy to HTTP)
  - Replacing or removing the FastAPI server transport
  - Interactive TUI experience
  - Shell-specific plugin distribution (Homebrew formula, distro packages) beyond documented pip/pipx install paths
  - Bypassing core tool validation, logging, or DB invariants

## Story 15.1: Shared Tool Executor and Adapter Refactor

Introduce a shared runtime execution path so HTTP and CLI adapters invoke the same validation, tool dispatch, transaction handling, hashing, and event logging logic.

Acceptance Criteria:
- Shared `execute_tool` runtime entrypoint exists and is used by HTTP adapter for tool dispatch.
- CLI adapter can invoke the same entrypoint with a trusted execution context.
- Auth/authz checks remain enforced for HTTP adapter.
- Trusted CLI bypasses auth/authz only, not validation/invariants/logging.
- Event logs distinguish CLI calls via execution context fields (e.g., `authn_method`, `actor_id`, `authorization_result`).
- Write-tool fail-closed logging behavior remains intact through shared path.

## Story 15.2: Packaged CLI Command, Command Surface, and Shell Integration

Implement a packaged `capital-os` CLI with strong shell ergonomics and discoverability, including completion and command help.

Acceptance Criteria:
- `pyproject.toml` vends a console script command `capital-os` (no `python -m` required for normal use).
- CLI framework provides nested commands and generated `--help` output.
- Commands exist for:
  - `capital-os health`
  - `capital-os tool list`
  - `capital-os tool schema <tool_name>`
  - `capital-os tool call <tool_name>`
  - `capital-os serve` (or `server run`) wrapper for existing HTTP mode
- `capital-os tool call` supports JSON payload input from file and stdin.
- Successful tool calls emit canonical JSON to stdout; errors emit structured output to stderr with non-zero exit codes.
- Shell completion is supported for `bash`, `zsh`, and `fish` (install/show completion flow documented and functional).
- Help text includes examples for key commands.

## Story 15.3: CLI/HTTP Parity Tests and Operator Documentation

Add parity coverage and docs to prevent semantic drift between adapters and ensure the CLI is easy to install and use.

Acceptance Criteria:
- Parity tests compare canonical responses/output hashes for selected tools via CLI and HTTP adapters on identical state/input.
- Tests verify CLI trusted-channel context is recorded in event logs.
- Docs cover install paths (`pip install -e .`, `pipx install .`) and CLI quickstart.
- Docs cover shell completion setup for `bash`, `zsh`, and `fish`.
- Tool reference documentation includes CLI examples alongside HTTP examples (where appropriate).
- `docs/current-state.md` reflects availability of the CLI adapter.

## Dependencies
- Existing tool registry/dispatch pattern in API runtime
- Existing schemas, domain services, observability hashing, and event logging contracts
- Existing Makefile/runtime controls from Epic 12 (CLI `serve` command may wrap or reuse them)

## Exit Criteria
1. Operators can run `capital-os tool call <tool>` locally without starting FastAPI.
2. CLI and HTTP adapters share a single canonical execution path for tool semantics.
3. CLI is installable as a real command via packaging metadata.
4. Shell UX is production-grade (help, examples, completion, stable output/error behavior).
5. Parity tests and docs reduce risk of adapter drift over time.
