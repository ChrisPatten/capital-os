-- up
PRAGMA foreign_keys = ON;

-- Opt-in recurrence metadata. Legacy `cadence` is left untouched; all new columns are NULL for existing rows.
-- funding_account_id intentionally has no REFERENCES clause (SQLite DROP COLUMN refuses FK columns);
-- existence is validated in the service layer.
ALTER TABLE obligations
ADD COLUMN recurrence TEXT CHECK (recurrence IN ('monthly','biweekly','quarterly','annual','one_time'));

ALTER TABLE obligations
ADD COLUMN day_of_month INTEGER CHECK (day_of_month BETWEEN 1 AND 31);

ALTER TABLE obligations
ADD COLUMN funding_account_id TEXT;

ALTER TABLE obligations
ADD COLUMN bucket TEXT CHECK (bucket IN ('recurring','debt','discretionary','savings','annual'));

-- down
-- ALTER TABLE obligations DROP COLUMN bucket;
-- ALTER TABLE obligations DROP COLUMN funding_account_id;
-- ALTER TABLE obligations DROP COLUMN day_of_month;
-- ALTER TABLE obligations DROP COLUMN recurrence;
