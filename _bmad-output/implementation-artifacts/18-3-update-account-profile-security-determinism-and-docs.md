# Story 18.3: `update_account_profile` Security, Determinism, and Documentation Hardening

Status: ready-for-dev

## Story

As a Capital OS maintainer,
I want full test and documentation hardening for account profile updates,
so that rename support is production-safe under auth, replay, and concurrency constraints.

## Acceptance Criteria

1. Integration tests cover schema errors (422), missing account (400), unauthorized (401), forbidden (403), and happy path.
2. Concurrency test verifies retry-safe deterministic behavior for duplicate idempotency keys.
3. Event log coverage exists for success and validation failure paths.
4. Determinism tests confirm stable `output_hash` for identical state/input.
5. Docs and skills are updated for `update_account_profile`, including guidance that history reads are direct SQL only.

## Tasks / Subtasks

- [ ] Task 1: Expand integration/security tests (AC: 1, 2, 3)
  - [ ] Add API-level tests for all error classes and auth/authz
  - [ ] Add concurrent duplicate request scenario
- [ ] Task 2: Add replay tests (AC: 4)
  - [ ] Verify output hash reproducibility across repeated runs
  - [ ] Verify canonical duplicate response hash stability
- [ ] Task 3: Update operator documentation and skills (AC: 5)
  - [ ] Update `docs/tool-reference.md`
  - [ ] Update `skills/CLAUDE_SKILL.md`
  - [ ] Update `skills/CODEX_SKILL.md`

## Dev Notes

### Architecture Compliance
- Preserve fail-closed write semantics when event logging fails.
- Keep no-read-tool decision explicit for this slice.

### File Structure Requirements
- New: `tests/integration/test_update_account_profile_security.py`
- New: `tests/replay/test_update_account_profile_replay.py`
- Modify: `docs/tool-reference.md`
- Modify: `skills/CLAUDE_SKILL.md`
- Modify: `skills/CODEX_SKILL.md`

### References
- [Source: `AGENTS.md`]
- [Source: `ARCHITECTURE.md`]
- [Source: `_bmad-output/planning-artifacts/epic-18-account-profile-and-identifier-evolution.md`]
