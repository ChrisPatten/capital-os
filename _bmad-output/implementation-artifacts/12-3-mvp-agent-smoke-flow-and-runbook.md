# Story 12.3: MVP Agent Smoke Flow and Runbook

Status: review

## Story

As a Capital OS tester,  
I want a one-command MVP smoke flow and concise operator runbook,  
so that I can reliably bootstrap, seed, run, and validate agent-driven API data creation.

## Acceptance Criteria

1. Provide a one-command smoke workflow that performs:
  - DB reset/migration
  - COA seed
  - API startup + health verification
  - representative write tool invocations:
    - `record_transaction_bundle`
    - `record_balance_snapshot`
    - `create_or_update_obligation`
  - representative read tool invocations confirming persisted state
2. Smoke workflow is deterministic and repeatable on clean DB.
3. Failures are actionable with step-level context and non-zero exit codes.
4. Add MVP operator runbook documenting:
  - environment setup and auth token defaults
  - bootstrap/run commands
  - expected success signatures
  - common failure signatures and recovery steps
5. Documentation explicitly states full Epic 11 portability features remain deferred.

## Tasks / Subtasks

- [x] Task 1: Implement smoke runner script/target (AC: 1, 2, 3)
  - [x] Add a script that sequences migrate -> seed -> serve/health -> API calls -> assertions.
  - [x] Use deterministic fixture payloads with stable IDs/dates for repeatability.
- [x] Task 2: Add tool-level assertions for write/read path (AC: 1, 2)
  - [x] Assert successful write responses and expected entities in read responses.
  - [x] Assert deterministic output properties where feasible.
- [x] Task 3: Add clear failure handling and exit semantics (AC: 3)
  - [x] Emit step name + cause on failure.
  - [x] Return non-zero for pipeline/CI usage.
- [x] Task 4: Publish MVP runbook (AC: 4, 5)
  - [x] Add doc section for “MVP Bootstrap and Agent Testing”.
  - [x] Clarify what is intentionally deferred to Epic 11.

## Notes

### Suggested Entry Points

- Make target:
  - `make mvp-smoke` (recommended)
- Script:
  - `scripts/mvp_smoke.py` (recommended)

### File Touchpoints / Implementation Notes

- `Makefile`
- `scripts/mvp_smoke.py` (new)
- `docs/README.md` and/or `README.md`
- Potential helper fixtures in `tests/support/`

## Definition of Done

- ACs 1-5 pass with reproducible command output.
- New user can execute smoke flow from a fresh checkout following runbook.
- Story status can be moved to `review` with evidence links.
