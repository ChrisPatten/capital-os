-- up
PRAGMA foreign_keys = ON;

ALTER TABLE obligations
ADD COLUMN fulfilled_by_transaction_id TEXT;

ALTER TABLE obligations
ADD COLUMN fulfilled_at TEXT;
