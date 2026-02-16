# Story 12.2: Makefile Runtime Controls and Serve-Idle

Status: ready-for-dev

## Story

As a Capital OS operator and agent runtime host,  
I want a deterministic Makefile control surface with idempotent `serve-idle`,  
so that repeated local automation can safely start, reuse, and stop API runtime.

## Acceptance Criteria

1. Add Makefile targets:
  - `init`
  - `migrate`
  - `coa-validate`
  - `coa-seed`
  - `health`
  - `run`
  - `stop`
  - `serve-idle`
2. Use runtime state files under `.run/`:
  - `.run/capital-os.pid`
  - `.run/capital-os.url`
  - `.run/last_request.ts`
  - `.run/uvicorn.log`
3. `make init` executes `migrate` then `coa-seed`.
4. `make run` starts uvicorn in background, writes PID + URL metadata, and behaves as no-op success if healthy server already exists.
5. `make stop` terminates tracked PID when possible and cleans `.run/*`.
6. `make serve-idle` uses health-first idempotence:
  - if `/health` is OK, exit 0
  - stale PID file does not block start
  - runtime shuts down after `CAPITAL_OS_IDLE_SECONDS` of inactivity
7. Wrapper script `scripts/serve_with_idle_shutdown.py` exists and manages last-request touch + idle termination.

## Tasks / Subtasks

- [ ] Task 1: Add Makefile target surface and defaults (AC: 1, 2, 3)
  - [ ] Define env defaults (`HOST`, `PORT`, `BASE_URL`, `CAPITAL_OS_DB_URL`, idle settings).
  - [ ] Create `.run/` lifecycle expectations in targets.
- [ ] Task 2: Implement run/health/stop semantics (AC: 4, 5)
  - [ ] Add health check via `curl -fsS $(BASE_URL)/health`.
  - [ ] Ensure healthy existing runtime returns no-op success for `run`.
  - [ ] Ensure `stop` handles missing/stale PID gracefully and cleans runtime files.
- [ ] Task 3: Implement idle-shutdown wrapper and wire `serve-idle` (AC: 6, 7)
  - [ ] Add `scripts/serve_with_idle_shutdown.py`.
  - [ ] Touch last-request timestamp on each request via middleware or app wrapping.
  - [ ] Enforce idle timeout termination and PID file cleanup.
- [ ] Task 4: Add runtime behavior tests/smoke assertions (AC: 4, 5, 6)
  - [ ] Add script-level integration/smoke checks for repeated `serve-idle`.
  - [ ] Verify stale PID scenario and health-first behavior.

## Notes

### Required Conventions

- `config/coa.yaml` is authoritative bootstrap input.
- Primary idempotence guard is `/health`; PID file is secondary.
- Repeated agent calls to `serve-idle` must be safe.

### File Touchpoints / Implementation Notes

- `Makefile` (new/updated)
- `scripts/serve_with_idle_shutdown.py` (new)
- `scripts/import_coa.py` (potential reuse from `coa-seed`)
- `src/capital_os/main.py` and/or `src/capital_os/api/app.py` (middleware hook if needed)
- Optional runtime smoke tests under `tests/integration/` or `tests/perf/`

## Definition of Done

- ACs 1-7 pass in local smoke checks.
- Repeated `make serve-idle` calls are demonstrably idempotent.
- Story status can be moved to `review` with command transcript evidence.
