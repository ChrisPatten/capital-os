-- rollback
DROP INDEX IF EXISTS idx_ledger_transactions_source_external;
DROP INDEX IF EXISTS idx_approval_proposals_created_id_status;
DROP INDEX IF EXISTS idx_obligations_due_id_active;
