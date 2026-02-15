DROP INDEX IF EXISTS idx_approval_proposals_entity_id_status_created;
DROP INDEX IF EXISTS idx_obligations_entity_id_active_due;
DROP INDEX IF EXISTS idx_snapshots_entity_id_account_date;
DROP INDEX IF EXISTS idx_transactions_entity_id_date;
DROP INDEX IF EXISTS idx_accounts_entity_id_code;

DROP TRIGGER IF EXISTS trg_approval_proposals_entity_id_immutable;
DROP TRIGGER IF EXISTS trg_ledger_transactions_append_only_update;
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
