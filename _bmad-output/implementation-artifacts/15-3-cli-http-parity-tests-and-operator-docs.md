# Story 15.3: CLI/HTTP Parity Tests and Operator Documentation

Status: ready-for-dev

## Story

As a Capital OS maintainer and operator,  
I want parity tests and clear CLI documentation,  
so that the trusted local CLI remains reliable, discoverable, and semantically aligned with the HTTP adapter.

## Acceptance Criteria

1. Parity tests run representative tool calls through both CLI and HTTP adapters and assert canonical response payload equivalence (excluding transport envelope differences) and matching `output_hash`.
2. Parity tests cover at least one write tool and one read/non-mutating tool.
3. Tests verify CLI event-log entries record trusted-channel execution context (e.g., `authn_method=trusted_cli`).
4. CLI validation failure tests assert deterministic machine-readable error payloads and non-zero exit behavior.
5. CLI tests cover `--db-path` selection behavior (success path on explicit temp DB and failure path on invalid path).
6. `README.md` and/or `docs/development-workflow.md` document CLI install and quickstart flows (`pip install -e .`, `pipx install .`).
7. Documentation includes shell completion setup for `bash`, `zsh`, and `fish`.
8. Documentation includes `--db-path` usage examples for local CLI commands.
9. `docs/tool-reference.md` includes CLI examples for tool invocation (local trusted channel) in addition to existing HTTP/API usage patterns where relevant.
10. `docs/current-state.md` reflects availability and scope of the CLI adapter (trusted local channel, HTTP still supported).

## Tasks / Subtasks

- [ ] Task 1: Add CLI parity integration tests (AC: 1, 2, 3)
  - [ ] Build test helpers for invoking CLI command and capturing stdout/stderr/exit code
  - [ ] Compare CLI vs HTTP canonical payloads/output hashes on identical DB state
  - [ ] Assert trusted CLI context fields in `event_log`
- [ ] Task 2: Add CLI failure/validation tests (AC: 4)
  - [ ] `--db-path` invalid/unreadable path -> structured error JSON on stderr + non-zero exit
  - [ ] Invalid payload path -> deterministic validation error JSON on stderr
  - [ ] Unknown tool -> deterministic error behavior and non-zero exit
- [ ] Task 3: Update operator and developer docs (AC: 6, 7, 8, 9, 10)
  - [ ] `README.md` install + quickstart
  - [ ] `docs/development-workflow.md` CLI workflow integration
  - [ ] Add `--db-path` examples and guidance for local DB targeting
  - [ ] `docs/tool-reference.md` CLI usage examples
  - [ ] `docs/current-state.md` runtime/adapter updates

## Dev Notes

### Testing Guidance

- Keep parity assertions focused on canonical tool payloads and `output_hash`, not transport-specific formatting.
- Normalize JSON parsing in tests before comparing outputs.
- Use stable fixtures to avoid false negatives from dynamic timestamps in non-canonical envelopes.

### References

- [Source: `_bmad-output/planning-artifacts/epic-15-cli-operator-interface.md`]
- [Source: `_bmad-output/implementation-artifacts/tech-spec-cli-operator-interface-delta-0223.md`]
- [Source: `docs/tool-reference.md`]
