-- up
PRAGMA foreign_keys = ON;

CREATE INDEX IF NOT EXISTS idx_obligations_due_id_active
ON obligations (next_due_date, obligation_id, active);

CREATE INDEX IF NOT EXISTS idx_approval_proposals_created_id_status
ON approval_proposals (created_at DESC, proposal_id, status);

CREATE INDEX IF NOT EXISTS idx_ledger_transactions_source_external
ON ledger_transactions (source_system, external_id);

-- down
-- DROP INDEX IF EXISTS idx_ledger_transactions_source_external;
-- DROP INDEX IF EXISTS idx_approval_proposals_created_id_status;
-- DROP INDEX IF EXISTS idx_obligations_due_id_active;
