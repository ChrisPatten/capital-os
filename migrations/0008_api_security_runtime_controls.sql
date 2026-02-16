-- up
PRAGMA foreign_keys = ON;

ALTER TABLE event_log
ADD COLUMN actor_id TEXT;

ALTER TABLE event_log
ADD COLUMN authn_method TEXT;

ALTER TABLE event_log
ADD COLUMN authorization_result TEXT;

ALTER TABLE event_log
ADD COLUMN violation_code TEXT;

CREATE INDEX IF NOT EXISTS idx_event_log_security_dimensions
ON event_log (tool_name, status, authorization_result, authn_method, created_at);
