# Capital OS Slimming Plan: Snapshots, Obligations, Budget

Status: proposed (Oct 23, 2026), approved in principle by Chris. Hand to an implementing agent.
Related: `CONSTITUTION.md`, `AGENTS.md`, `ARCHITECTURE.md`, `docs/adr/`, `.claude/skills/capital-os/SKILL.md` (Peggy's operating runbook), `scripts/capos` (Peggy's wrapper, repo root `scripts/`).

## 1. Why

Capital OS was built as a full double-entry ledger with approvals, periods, policy rules, Plaid and an import inbox. In practice the household uses it for two things: balance snapshots and obligations (bills). A third need has appeared: a structured current budget and a cash-flow forecast.

Measured on the live DB (Oct 23, 2026):
- `balance_snapshots`: 445 rows since 2024-07, roughly 30 a month, latest 2026-10-16. Actively used.
- `obligations`: 28 rows (8 active, 20 inactive). `list_obligations` was called about 2,800 times since Aug (morning brief, Kindle). Writes go through `scripts/capos bill`.
- `ledger_transactions`: 1,922 rows / 3,844 postings. Bulk imports stopped mid-2026: Apple Card to Aug 3, SFCU CSV to Jul 31, Citizens to Apr 20, Amex to Jul 17. Only a handful of manual entries since.
- `approval_proposals`: 106 total (86 committed, 5 rejected, 15 still `proposed`, oldest 2026-03-26). Triggered by the >$1,000 / duplicate-match rule; nobody reviews them.
- Zero rows in `accounting_periods`, `policy_rules`, `plaid_*`, `inbox_*`.
- Spending analysis (`discretionary-spend` skill) reads bank CSVs in `data/financial/` directly, not the ledger.

Goal: make the day-to-day surface match real use, without breaking any constitutional invariant and without deleting history.

## 2. Hard constraints (do not violate)

From `CONSTITUTION.md` and `AGENTS.md` (document precedence: CONSTITUTION > AGENTS > ARCHITECTURE > tech specs > PRD):
- Never delete or UPDATE append-only history (transactions, postings, event log). Corrections are compensating entries. This plan freezes the ledger; it does not remove it.
- `sum(postings.amount) == 0`, `NUMERIC(20,4)` round-half-even, UTC timestamps, idempotency on `(source_system, external_id)`, cycle rejection: all unchanged.
- Determinism: identical state + identical inputs must give identical `output_hash`. New tools must take an explicit `as_of_date`; never read the wall clock inside a tool.
- Every tool invocation (success and failure) emits an event-log record (`tool_name`, `correlation_id`, `input_hash`, `output_hash`, `timestamp`, `duration`). Write tools fail closed if event logging fails.
- Writes only through the service/tool layer. No direct SQL writes. Read-only consumers use read-only connections.
- Schema changes: numbered SQL migration plus a `.rollback.sql` counterpart, rollback tested via `scripts/check_migration_cycle.py`. Next number is `0013`: `0011`/`0012` are the parked inbox/Plaid migrations, already applied to the live DB, so they stay reserved.
- Any change to invariants, hashing or idempotency semantics requires an ADR. This plan should not need that; if you find it does, stop and write the ADR first (`docs/adr/ADR-00N-*.md`, format as ADR-001: Status, Date, Deciders, Related, Context, Decision, Rationale, Consequences).
- No secrets in event payloads. Production runtime makes zero outbound network calls.
- Layering: API/tools -> domain services -> repository/DB. Tools stay thin; new logic goes in `src/capital_os/domain/*`.
- Pydantic schemas in `src/capital_os/schemas/`; validation failures return machine-readable 4xx shapes.
- Each new write/read tool needs its capability mapping (`tools:read` / `tools:write`) and must be exposed through `mcp/server.py` and the local `capital-os tool` CLI.

## 3. Safety rules for the live database

- The live DB is `capital-os/data/capital_os.db` (gitignored). Peggy and Chris use it daily. Before any migration run against it: copy it to `data/backups/capital_os-YYYYMMDD-HHMMSS.db` (use `sqlite3 .backup`, not `cp`, while WAL is active).
- Develop and test against a copy (`CAPITAL_OS_DB_URL=sqlite:///./data/dev-copy.db`), never the live file.
- Do not run `make mvp-smoke` or anything that resets the DB against the live file.
- Do not create accounts without Chris's approval (existing household rule). Do not approve proposed transactions without his review.
- Do not change the `capital-os` skill or `scripts/capos` behavior in ways that break existing commands (`capos sql`, `capos bill`, `list_obligations`, `record_balance_snapshot`, `get_account_balances`). Those are called by the morning brief, Kindle refresh and email scan. Additive changes only; coordinate with Peggy for anything else.

## 4. Work items

Do them in order. Each item is its own PR/commit set with tests green before the next starts.

### Item 1: Freeze the ledger, retire the approvals flow (operational, no schema change)

1. Set `CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT` high enough that nothing proposes (or add an explicit `approval_enabled=false` setting in `config.py`, default true so existing tests are unaffected). Document it in `CLAUDE.md` and the env table.
2. Decide what happens to `record_transaction_bundle`: keep it working (manual entries, such as "water paid from SFCU checking", still happen and fulfill obligations) but no longer require imports. Do not remove it.
3. The 15 pending proposals: list them (`list_proposals`), summarize each for Chris (date, amount, accounts, match reason), and ask him to reject or approve. Do not decide for him.
4. Update `docs/current-state.md` and the Peggy skill text to say: ledger is frozen history plus manual entries; imports are discontinued.
5. Tests: config flag on/off, existing approval tests unchanged with flag on.

Acceptance: a >$1,000 manual transaction commits without a proposal when the flag is off; with the flag on, behavior is identical to today.

### Item 2: Recurring obligations with a funding account (migration 0013)

Problem: today every bill creates a new obligation named `"<Payee> - <Mon YYYY> (<ref>)"`, then it is fulfilled and goes inactive. There is no concept of a recurring commitment, and no record of which account pays it.

Design:
- Add nullable columns to `obligations`: `cadence` (`monthly|biweekly|quarterly|annual|one_time`), `day_of_month` (1-31, nullable), `funding_account_id` (FK to `accounts`, nullable), `bucket` (`recurring|debt|discretionary|savings|annual`, nullable). Defaults keep existing rows valid (all NULL).
- `fulfill_obligation`: when the obligation has a cadence, roll `next_due_date` forward by one cycle and keep it active, instead of deactivating. One-time obligations behave exactly as today. Rolling must be deterministic and month-end safe (day 31 in a 30-day month clamps to the last day; weekend adjustment is NOT applied in the ledger, that is a forecast concern).
- `create_or_update_obligation` accepts the new fields (optional). Existing payloads still validate and produce the same hashes where the new fields are absent. Add a replay test proving old payload hashes are unchanged.
- `list_obligations` returns the new fields.
- Migration includes `0013_*.rollback.sql`. SQLite cannot drop columns on older versions, so rollback may rebuild the table; test it with `check_migration_cycle.py`.
- Backfill after migration (a data step, done through the tool, not SQL): set cadence/day/funding account/bucket for the currently active obligations and the recurring items in section 6. Chris's current budget is the source of truth.

Acceptance: fulfilling a monthly mortgage obligation on Nov 3 leaves it active with `next_due_date` Dec; fulfilling a one-time bill deactivates it as before; old payloads and old rows work unchanged.

### Item 3: Budget as data (migration 0014)

Problem: the current budget lives in markdown (`memory/project_budget_allocation.md`), so breakdowns and forecasts are recomputed by hand.

Design:
- New table `budget_items`: `item_id`, `name`, `amount` (NUMERIC(20,4)), `cadence`, `day_of_month`, `funding_account_id`, `bucket` (`recurring|debt|discretionary|savings|annual`), `active`, `effective_date`, `source` (free text), plus created/updated audit fields. Budget items are versioned by `effective_date`, never edited in place: a change inserts a new row and deactivates the old one (history stays queryable, matching the "current plus archive" practice).
- Also a small `income_streams` table or equivalent budget rows: payroll deposit amount, schedule (biweekly anchor date), destination account. Chris's payroll is $2,960 to Citizens every other Thursday (anchor 2026-10-29), with other splits to SFCU accounts.
- Tools: `upsert_budget_item` (write), `list_budget_items` (read), `get_budget_summary` (read; totals by bucket and percent of take-home, per-account surplus/deficit). Go through the standard schema, capability, event-log and hashing path.
- Migration `0014_*` plus rollback; tests for versioning, summary math (decimal rounding, 26/12 monthly conversion for biweekly items), and replay hash reproducibility.

Acceptance: `get_budget_summary` reproduces the Oct 23, 2026 breakdown in section 6 (recurring $6,374, debt paydown $1,090, annual $166, discretionary $700, savings $487.50, Kate's deposit $3,274, leftover about $501 per month) from the seeded rows.

### Item 4: Forecast tool (no new tables)

- `forecast_cash(account_id, as_of_date, days, starting_balance?)` (read). Starting balance defaults to the latest snapshot on or before `as_of_date`, adjusted by obligations/budget items already due between the snapshot date and `as_of_date` only if the caller asks (`include_unposted=true`); default is the plain snapshot so the result is deterministic and explainable.
- Events: budget items and obligations funded by that account (by `day_of_month`, weekend dates move to the next business day) and income streams (biweekly from the anchor date).
- Output: dated event list, running balance, per-month minimum balance with the date and item that caused it, overall minimum, and a `below_threshold` flag for a caller-supplied threshold (for example 200).
- Deterministic: `as_of_date` is required; no wall clock. Pure function of DB state plus inputs.
- Acceptance test: seed section 6 and reproduce the Oct 23, 2026 Citizens model (start 5,116.31 on 2026-10-19; lowest 2,376.74 on 2027-01-05; monthly lows Oct 3,994.58, Nov 2,636.74, Dec 2,506.74, Jan 2,376.74, Feb 3,120.74, Mar 2,990.74).

### Item 5: Auto-match payments to obligations

- A script (not a Capital OS runtime feature, because the runtime makes no outbound calls and reads no files outside the DB) in `scripts/` that reads the bank CSVs under `data/financial/` and, for each debit that matches an active obligation (payee keyword, amount within tolerance, date window), calls `fulfill_obligation`. Dry-run by default, prints proposed matches, applies only with `--apply`.
- Keep it idempotent: matches keyed on the CSV row, replays do nothing.
- Do not write ledger transactions for matched payments; fulfillment only.
- Tests with a fixture CSV.

### Item 6: Cleanup

- Archive view: `list_obligations` gains `include_inactive` (default false; verify current default and keep it) so the 20 stale obligations stop cluttering default output. No deletes.
- Mark unused accounts inactive via `update_account_metadata` (list candidates for Chris first; do not create or remove accounts).
- Trim `.claude/skills/capital-os/SKILL.md` and `references/accounts.md` to what is actually used (snapshots, obligations, `bill`, budget, forecast). Keep proposals/transfers/imports as a short "frozen" appendix.
- Update `docs/` (`current-state.md`, `api-contracts.md`, `data-model.md`) to match.

## 5. Out of scope

- Removing tables, tools or history. Plaid, periods, policy and inbox stay dormant, not deleted.
- New ingestion pipelines, UI, or any outbound network call from the runtime.
- Changing hashing, idempotency or the posting-balance invariant.
- Importing historical transactions into the ledger.

## 6. Reference data for seeding and tests (Chris, Oct 23, 2026)

Source of truth: `memory/project_budget_allocation.md` (current) and `memory/archive/budget/` (history). Take-home is $5,811.75 per paycheck, biweekly (about $12,592/mo at 26/12).

Direct deposit per paycheck: Citizens (7819) $2,959.00 (actual deposits have been $2,960); Shrewsbury FCU K (Kate, 8051) $1,511.00 (not tracked); SFCU Checking (4058, ledger `ast_cash_shrewsbury_checking_77`) $1,341.75. Auto-transfer SFCU Checking -> Savings (01): $243.75 per paycheck planned; actual $245.00 every other Friday.

Citizens (`ast_cash_citizens_checking_7819`), monthly:
- Life insurance 40.38 (1st); Rocket mortgage 3,127.46 (3rd); Arbella 276 (3rd); Discover paydown 590 (5th); Eversource gas 284 (5th); Fios 89.99 (about 12th); Firstmark student loan 520.44 (about 18th); Apple Card paydown 500 (check, about 24th); Highlander (TD) 461 (about 26th); Verizon wireless 160.73 (28th). Total 6,050.00. Payroll 2,960 every other Thursday from 2026-10-29.

SFCU Checking (77), monthly:
- OhDeer mosquito control 117 (about every 3 weeks, counted monthly), GBH 10, GBH 10, Visible (J's phone) 25, Wyze 11.73, electric 265, water 166 (about 500 per quarter), Jeep 543 (post-refi), train/parking 150. Plus discretionary 700 and savings 487.50.

Apple Card (charged there): Apple One 37.95, SiriusXM 6.06, NYT Games 5.99, iCloud+ 9.99. Amex: Dropbox 12.74, WGBH 10, charity: water 10, Xbox Game Pass 24.43.

Annual: Amazon Prime 139 (October), Jeep/Highlander excise 800, tax prep 200, car maintenance 500, dog medications 350 (averaged 165.75/mo).

Live snapshot facts for the Citizens forecast test: snapshot 2026-10-16 = 5,636.75; Firstmark 520.44 debited 2026-10-19; model start 5,116.31.

## 7. Definition of done

- `pytest` full suite green, including new unit, integration, replay-hash and security tests; `pytest -m performance` p95 < 300 ms on the reference dataset for any new read tool.
- `python scripts/check_migration_cycle.py --db-path /tmp/capital-os-migration-cycle.db` passes for 0013 and 0014.
- CI gates in `.github/workflows/ci.yml` (tests, migration-reversibility, determinism-regression, security-auth-surface, epic8 gates) all pass.
- Existing replay hashes for old payloads are unchanged.
- Docs updated; `AGENTS.md` / `CLAUDE.md` mention the frozen-ledger stance and the new tools.
- A backup of the live DB exists before any migration is applied to it, and Chris has been told the migration is about to run.
- Report back with: what changed per item, test output, anything that needed an ADR, and anything skipped.
