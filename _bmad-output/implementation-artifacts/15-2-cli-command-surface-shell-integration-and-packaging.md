# Story 15.2: CLI Command Surface, Shell Integration, and Packaging

Status: done

## Story

As a Capital OS operator,  
I want an installable `capital-os` CLI with strong shell ergonomics,  
so that I can invoke tools locally with discoverable commands, good help text, and tab completion.

## Acceptance Criteria

1. `pyproject.toml` exposes a console script command `capital-os` (normal usage does not require `python -m`).
2. CLI root command and nested subcommands are implemented using a framework with high-quality generated help and shell completion support.
3. CLI supports:
   - `capital-os health`
   - `capital-os tool list`
   - `capital-os tool schema <tool_name>`
   - `capital-os tool call <tool_name>`
   - `capital-os serve` (or equivalent command wrapping existing server startup)
4. `capital-os tool call` accepts JSON payload input from file and stdin (and optionally inline JSON).
5. Successful `tool call` writes canonical JSON response payload to stdout and exits `0`.
6. Errors emit structured error output to stderr with non-zero exit codes, preserving deterministic error payloads where applicable.
7. CLI `--help` output includes examples for the root command and `tool call`.
8. Shell completion is available for `bash`, `zsh`, and `fish`, with documented setup flow.
9. Local-mode CLI commands support selecting the SQLite database file via `--db-path` (global option or command option), and use the provided path for execution.
10. Invalid or unreadable `--db-path` values return structured error output on stderr and a non-zero exit code.

## Tasks / Subtasks

- [x] Task 1: Add CLI package and root command (AC: 2, 3, 7)
  - [x] Create `src/capital_os/cli/main.py`
  - [x] Add nested command groups/modules (`tool`, `server` or `serve`)
  - [x] Include command examples in help text/docstrings
- [x] Task 2: Add packaging entrypoint (AC: 1)
  - [x] Update `pyproject.toml` `[project.scripts]` with `capital-os = capital_os.cli.main:...`
  - [x] Verify editable install exposes command in local env
- [x] Task 3: Implement CLI command handlers (AC: 3, 4, 5, 6)
  - [x] `health` command
  - [x] `tool list` command
  - [x] `tool schema <tool_name>` command
  - [x] `tool call <tool_name>` command with file/stdin JSON ingestion
  - [x] `serve` command wrapper
- [x] Task 4: Output and exit-code discipline (AC: 5, 6)
  - [x] JSON stdout for success
  - [x] stderr for errors
  - [x] Stable exit code mapping
- [x] Task 5: Shell completion support (AC: 8)
  - [x] Wire framework completion commands/features
  - [x] Validate completion generation for `bash`, `zsh`, and `fish`
- [x] Task 6: DB path selection support (AC: 9, 10)
  - [x] Add `--db-path` option wiring for local-mode commands
  - [x] Ensure shared runtime/session initialization uses provided path
  - [x] Add error handling for missing/unopenable database paths

## Dev Notes

### Technical Requirements

- Recommended framework: `Typer` (Click-based) for nested commands, typed options, `--help`, and completion support.
- CLI is a trusted local adapter and should inject execution context via story 15.1 shared executor integration.
- `tool call` should be script-friendly first (JSON IO), human readability second.
- Prefer one consistent `--db-path` option contract across all local commands instead of mixed option/env-only behavior.

### File Structure Requirements

- New: `src/capital_os/cli/main.py`
- New: `src/capital_os/cli/tool.py`
- New: `src/capital_os/cli/server.py` (or similar)
- New: `src/capital_os/cli/context.py`
- Modify: `pyproject.toml`

### References

- [Source: `_bmad-output/planning-artifacts/epic-15-cli-operator-interface.md`]
- [Source: `_bmad-output/implementation-artifacts/tech-spec-cli-operator-interface-delta-0223.md`]
