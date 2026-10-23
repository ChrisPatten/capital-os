-- rollback
ALTER TABLE obligations DROP COLUMN bucket;
ALTER TABLE obligations DROP COLUMN funding_account_id;
ALTER TABLE obligations DROP COLUMN day_of_month;
ALTER TABLE obligations DROP COLUMN recurrence;
