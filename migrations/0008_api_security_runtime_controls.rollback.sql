-- rollback
DROP INDEX IF EXISTS idx_event_log_security_dimensions;

ALTER TABLE event_log DROP COLUMN violation_code;
ALTER TABLE event_log DROP COLUMN authorization_result;
ALTER TABLE event_log DROP COLUMN authn_method;
ALTER TABLE event_log DROP COLUMN actor_id;
