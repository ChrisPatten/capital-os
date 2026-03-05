-- up
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS account_identifier_history (
  history_id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(account_id),
  source_system TEXT NOT NULL,
  external_id TEXT NOT NULL,
  institution_suffix TEXT,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  correlation_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_account_identifier_history_account_source_from
ON account_identifier_history (account_id, source_system, valid_from DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_account_identifier_history_active
ON account_identifier_history (account_id, source_system)
WHERE valid_to IS NULL;

CREATE TRIGGER IF NOT EXISTS trg_account_identifier_history_append_only_update
BEFORE UPDATE ON account_identifier_history
FOR EACH ROW
WHEN NOT (
  OLD.valid_to IS NULL
  AND NEW.valid_to IS NOT NULL
  AND NEW.history_id = OLD.history_id
  AND NEW.account_id = OLD.account_id
  AND NEW.source_system = OLD.source_system
  AND NEW.external_id = OLD.external_id
  AND (
    (NEW.institution_suffix IS NULL AND OLD.institution_suffix IS NULL)
    OR NEW.institution_suffix = OLD.institution_suffix
  )
  AND NEW.valid_from = OLD.valid_from
  AND NEW.correlation_id = OLD.correlation_id
  AND NEW.created_at = OLD.created_at
)
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: account_identifier_history UPDATE not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_account_identifier_history_append_only_delete
BEFORE DELETE ON account_identifier_history
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: account_identifier_history DELETE not permitted');
END;

-- down
-- DROP TRIGGER IF EXISTS trg_account_identifier_history_append_only_delete;
-- DROP TRIGGER IF EXISTS trg_account_identifier_history_append_only_update;
-- DROP INDEX IF EXISTS idx_account_identifier_history_active;
-- DROP INDEX IF EXISTS idx_account_identifier_history_account_source_from;
-- DROP TABLE IF EXISTS account_identifier_history;
