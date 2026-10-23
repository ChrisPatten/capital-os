# Payment auto-match (offline)

`scripts/match_obligation_payments.py` reads bank CSV exports and fulfills the active obligations they pay. It is an offline script on purpose: the Capital OS runtime reads no files outside its DB and makes no outbound calls.

```bash
# dry run (default): prints proposed / ambiguous / unmatched, changes no obligation
.venv/bin/python scripts/match_obligation_payments.py --db-path data/capital_os.db --since 2026-09-01

# apply: calls fulfill_obligation once per proposed match
.venv/bin/python scripts/match_obligation_payments.py --db-path data/capital_os.db --since 2026-09-01 --apply
```

Options: `--data-dir` (default `~/workspace/peggy-claude-code/data/financial`, with `citizens/`, `sfcu/`, `apple_card/`, `personal_amex/` subfolders), `--amount-tolerance-pct` (1), `--amount-tolerance-min` (1.00), `--days-before` (5), `--days-after` (10), `--since YYYY-MM-DD`, `--json`. Exit 0 ok, 2 bad arguments or missing paths.

## Matching rule

A debit matches an active obligation when all of these hold:

1. Keywords. If `metadata.match_keywords` (list of strings) exists, every keyword must appear in the debit text (case-insensitive). Otherwise keywords come from the name: text before `" - "`, lowercased, split into words of 4+ letters, with generic bill words dropped (payment, loan, insurance, mortgage, card, student, ...); a debit matches if any one of them appears. Parenthesized text is kept because real names put the payee there, for example `Student loan payment (Firstmark)`.
2. Amount within `max(tolerance-min, tolerance-pct of expected_amount)`.
3. Debit date within `[next_due_date - days-before, next_due_date + days-after]`.

One candidate debit that matches no other obligation is a proposed match. Several candidates, or a debit shared by several obligations, is reported as ambiguous and never applied. Payees whose bank text differs from the obligation name (for example "TD Auto Finance" for the Highlander loan, "AMEX EPAYMENT" for the Amex bill) need `metadata.match_keywords`, e.g. `["td auto"]`.

Debit text: Citizens description; SFCU description plus memo (two export layouts are handled); Apple Card description plus merchant (payments and credits skipped); Amex description (credits skipped). Unknown folders and unrecognized file headers are skipped with a warning.

## Safety

- Writes only through `fulfill_obligation` via `execute_tool`. It never records ledger transactions or balance snapshots.
- Each call passes `expected_due_date = next_due_date` (replay guard), `fulfilled_at = <debit date>T12:00:00Z`, and `correlation_id = automatch-<first 16 hex of sha256(bank + file + raw row)>`. Re-running after an apply is a no-op: recurring rows have rolled forward and one-time rows are inactive; a stale proposal reports `already_fulfilled`.
- Even a dry run calls `list_obligations`, which, like every tool call, appends an event-log row. No obligation or ledger data changes.
- CSVs hold real household data: they stay outside the repo; tests use synthetic fixtures in `tests/fixtures/bank_csv/`.
- Back up the DB before the first `--apply` against live data.
