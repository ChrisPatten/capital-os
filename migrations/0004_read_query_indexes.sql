-- up
PRAGMA foreign_keys = ON;

CREATE INDEX IF NOT EXISTS idx_accounts_code_account_id
ON accounts (code, account_id);

CREATE INDEX IF NOT EXISTS idx_accounts_parent_code_account_id
ON accounts (parent_account_id, code, account_id);

CREATE INDEX IF NOT EXISTS idx_ledger_transactions_date_id
ON ledger_transactions (transaction_date, transaction_id);

CREATE INDEX IF NOT EXISTS idx_ledger_postings_account_transaction
ON ledger_postings (account_id, transaction_id);

CREATE INDEX IF NOT EXISTS idx_balance_snapshots_account_date
ON balance_snapshots (account_id, snapshot_date DESC, snapshot_id DESC);

-- down
-- DROP INDEX IF EXISTS idx_balance_snapshots_account_date;
-- DROP INDEX IF EXISTS idx_ledger_postings_account_transaction;
-- DROP INDEX IF EXISTS idx_ledger_transactions_date_id;
-- DROP INDEX IF EXISTS idx_accounts_parent_code_account_id;
-- DROP INDEX IF EXISTS idx_accounts_code_account_id;
