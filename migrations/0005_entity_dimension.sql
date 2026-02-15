-- up
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO entities (entity_id, code, name, metadata)
VALUES ('entity-default', 'DEFAULT', 'Default Entity', '{}')
ON CONFLICT(entity_id) DO NOTHING;

ALTER TABLE accounts
ADD COLUMN entity_id TEXT NOT NULL DEFAULT 'entity-default' REFERENCES entities(entity_id);

ALTER TABLE ledger_transactions
ADD COLUMN entity_id TEXT NOT NULL DEFAULT 'entity-default' REFERENCES entities(entity_id);

ALTER TABLE balance_snapshots
ADD COLUMN entity_id TEXT NOT NULL DEFAULT 'entity-default' REFERENCES entities(entity_id);

ALTER TABLE obligations
ADD COLUMN entity_id TEXT NOT NULL DEFAULT 'entity-default' REFERENCES entities(entity_id);

ALTER TABLE approval_proposals
ADD COLUMN entity_id TEXT NOT NULL DEFAULT 'entity-default' REFERENCES entities(entity_id);

CREATE INDEX IF NOT EXISTS idx_accounts_entity_id_code
ON accounts (entity_id, code, account_id);

CREATE INDEX IF NOT EXISTS idx_transactions_entity_id_date
ON ledger_transactions (entity_id, transaction_date, transaction_id);

CREATE INDEX IF NOT EXISTS idx_snapshots_entity_id_account_date
ON balance_snapshots (entity_id, account_id, snapshot_date DESC, snapshot_id DESC);

CREATE INDEX IF NOT EXISTS idx_obligations_entity_id_active_due
ON obligations (entity_id, active, next_due_date, obligation_id);

CREATE INDEX IF NOT EXISTS idx_approval_proposals_entity_id_status_created
ON approval_proposals (entity_id, status, created_at, proposal_id);

CREATE TRIGGER IF NOT EXISTS trg_approval_proposals_entity_id_immutable
BEFORE UPDATE OF entity_id ON approval_proposals
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'approval_proposals.entity_id is immutable');
END;

DROP TRIGGER IF EXISTS trg_ledger_transactions_append_only_update;
CREATE TRIGGER trg_ledger_transactions_append_only_update
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
  AND NEW.entity_id = OLD.entity_id
  AND NEW.created_at = OLD.created_at
)
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: ledger_transactions UPDATE not permitted');
END;

-- down
-- DROP INDEX IF EXISTS idx_approval_proposals_entity_id_status_created;
-- DROP INDEX IF EXISTS idx_obligations_entity_id_active_due;
-- DROP INDEX IF EXISTS idx_snapshots_entity_id_account_date;
-- DROP INDEX IF EXISTS idx_transactions_entity_id_date;
-- DROP INDEX IF EXISTS idx_accounts_entity_id_code;
-- DROP TRIGGER IF EXISTS trg_approval_proposals_entity_id_immutable;
-- DROP TRIGGER IF EXISTS trg_ledger_transactions_append_only_update;
