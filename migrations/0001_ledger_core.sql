-- up
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
  account_id TEXT PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  account_type TEXT NOT NULL CHECK (account_type IN ('asset','liability','equity','income','expense')),
  parent_account_id TEXT REFERENCES accounts(account_id),
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ledger_transactions (
  transaction_id TEXT PRIMARY KEY,
  source_system TEXT NOT NULL,
  external_id TEXT NOT NULL,
  transaction_date TEXT NOT NULL,
  description TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output_hash TEXT,
  response_payload TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (source_system, external_id)
);

CREATE TABLE IF NOT EXISTS ledger_postings (
  posting_id TEXT PRIMARY KEY,
  transaction_id TEXT NOT NULL REFERENCES ledger_transactions(transaction_id),
  account_id TEXT NOT NULL REFERENCES accounts(account_id),
  amount NUMERIC NOT NULL,
  currency TEXT NOT NULL CHECK (currency = 'USD'),
  memo TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS balance_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  source_system TEXT NOT NULL,
  account_id TEXT NOT NULL REFERENCES accounts(account_id),
  snapshot_date TEXT NOT NULL,
  balance NUMERIC NOT NULL,
  currency TEXT NOT NULL CHECK (currency = 'USD'),
  source_artifact_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (account_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS obligations (
  obligation_id TEXT PRIMARY KEY,
  source_system TEXT NOT NULL,
  name TEXT NOT NULL,
  account_id TEXT NOT NULL REFERENCES accounts(account_id),
  cadence TEXT NOT NULL CHECK (cadence IN ('monthly','annual','custom')),
  expected_amount NUMERIC NOT NULL,
  variability_flag INTEGER NOT NULL DEFAULT 0,
  next_due_date TEXT NOT NULL,
  metadata TEXT NOT NULL DEFAULT '{}',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (source_system, name, account_id)
);

CREATE TABLE IF NOT EXISTS event_log (
  event_id TEXT PRIMARY KEY,
  tool_name TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output_hash TEXT NOT NULL,
  event_timestamp TEXT NOT NULL,
  duration_ms INTEGER NOT NULL,
  status TEXT NOT NULL,
  error_code TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS trg_prevent_account_cycle_insert
BEFORE INSERT ON accounts
FOR EACH ROW
WHEN NEW.parent_account_id IS NOT NULL
BEGIN
  SELECT RAISE(ABORT, 'Account cycle detected')
  WHERE NEW.parent_account_id = NEW.account_id;

  SELECT RAISE(ABORT, 'Account cycle detected')
  WHERE EXISTS (
    WITH RECURSIVE ancestors(account_id, parent_account_id) AS (
      SELECT account_id, parent_account_id FROM accounts WHERE account_id = NEW.parent_account_id
      UNION ALL
      SELECT a.account_id, a.parent_account_id
      FROM accounts a
      JOIN ancestors an ON a.account_id = an.parent_account_id
      WHERE an.parent_account_id IS NOT NULL
    )
    SELECT 1 FROM ancestors WHERE account_id = NEW.account_id
  );
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_account_cycle_update
BEFORE UPDATE OF parent_account_id ON accounts
FOR EACH ROW
WHEN NEW.parent_account_id IS NOT NULL
BEGIN
  SELECT RAISE(ABORT, 'Account cycle detected')
  WHERE NEW.parent_account_id = NEW.account_id;

  SELECT RAISE(ABORT, 'Account cycle detected')
  WHERE EXISTS (
    WITH RECURSIVE ancestors(account_id, parent_account_id) AS (
      SELECT account_id, parent_account_id FROM accounts WHERE account_id = NEW.parent_account_id
      UNION ALL
      SELECT a.account_id, a.parent_account_id
      FROM accounts a
      JOIN ancestors an ON a.account_id = an.parent_account_id
      WHERE an.parent_account_id IS NOT NULL
    )
    SELECT 1 FROM ancestors WHERE account_id = NEW.account_id
  );
END;

-- down
-- DROP TRIGGER IF EXISTS trg_prevent_account_cycle_update;
-- DROP TRIGGER IF EXISTS trg_prevent_account_cycle_insert;
-- DROP TABLE IF EXISTS event_log;
-- DROP TABLE IF EXISTS obligations;
-- DROP TABLE IF EXISTS balance_snapshots;
-- DROP TABLE IF EXISTS ledger_postings;
-- DROP TABLE IF EXISTS ledger_transactions;
-- DROP TABLE IF EXISTS accounts;
