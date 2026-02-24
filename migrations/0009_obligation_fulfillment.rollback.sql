-- rollback
ALTER TABLE obligations DROP COLUMN fulfilled_at;
ALTER TABLE obligations DROP COLUMN fulfilled_by_transaction_id;
