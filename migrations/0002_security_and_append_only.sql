-- up
PRAGMA foreign_keys = ON;

CREATE TRIGGER IF NOT EXISTS trg_ledger_transactions_append_only_update
BEFORE UPDATE ON ledger_transactions
FOR EACH ROW
WHEN NOT (
  OLD.response_payload IS NULL
  AND OLD.output_hash IS NULL
  AND NEW.response_payload IS NOT NULL
  AND NEW.output_hash IS NOT NULL
  AND NEW.transaction_id = OLD.transaction_id
  AND NEW.source_system = OLD.source_system
  AND NEW.external_id = OLD.external_id
  AND NEW.transaction_date = OLD.transaction_date
  AND NEW.description = OLD.description
  AND NEW.correlation_id = OLD.correlation_id
  AND NEW.input_hash = OLD.input_hash
  AND NEW.created_at = OLD.created_at
)
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: ledger_transactions UPDATE not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_ledger_transactions_append_only_delete
BEFORE DELETE ON ledger_transactions
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: ledger_transactions DELETE not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_ledger_postings_append_only_update
BEFORE UPDATE ON ledger_postings
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: ledger_postings UPDATE not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_ledger_postings_append_only_delete
BEFORE DELETE ON ledger_postings
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: ledger_postings DELETE not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_event_log_append_only_update
BEFORE UPDATE ON event_log
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: event_log UPDATE not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_event_log_append_only_delete
BEFORE DELETE ON event_log
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: event_log DELETE not permitted');
END;

-- down
-- DROP TRIGGER IF EXISTS trg_event_log_append_only_delete;
-- DROP TRIGGER IF EXISTS trg_event_log_append_only_update;
-- DROP TRIGGER IF EXISTS trg_ledger_postings_append_only_delete;
-- DROP TRIGGER IF EXISTS trg_ledger_postings_append_only_update;
-- DROP TRIGGER IF EXISTS trg_ledger_transactions_append_only_delete;
-- DROP TRIGGER IF EXISTS trg_ledger_transactions_append_only_update;
