-- up
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounting_periods (
  period_id TEXT PRIMARY KEY,
  period_key TEXT NOT NULL,
  entity_id TEXT NOT NULL DEFAULT 'entity-default' REFERENCES entities(entity_id),
  status TEXT NOT NULL CHECK (status IN ('open','closed','locked')),
  actor_id TEXT,
  correlation_id TEXT,
  closed_at TEXT,
  locked_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (period_key, entity_id)
);

CREATE TRIGGER IF NOT EXISTS trg_accounting_periods_set_updated_at
AFTER UPDATE ON accounting_periods
FOR EACH ROW
BEGIN
  UPDATE accounting_periods
  SET updated_at = CURRENT_TIMESTAMP
  WHERE period_id = NEW.period_id;
END;

CREATE TABLE IF NOT EXISTS policy_rules (
  rule_id TEXT PRIMARY KEY,
  priority INTEGER NOT NULL,
  tool_name TEXT,
  entity_id TEXT REFERENCES entities(entity_id),
  transaction_category TEXT,
  risk_band TEXT,
  velocity_limit_count INTEGER,
  velocity_window_seconds INTEGER,
  threshold_amount NUMERIC NOT NULL,
  required_approvals INTEGER NOT NULL DEFAULT 1,
  active INTEGER NOT NULL DEFAULT 1,
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (required_approvals >= 1),
  CHECK (
    (velocity_limit_count IS NULL AND velocity_window_seconds IS NULL)
    OR (velocity_limit_count IS NOT NULL AND velocity_window_seconds IS NOT NULL AND velocity_limit_count >= 1 AND velocity_window_seconds >= 1)
  )
);

ALTER TABLE ledger_transactions
ADD COLUMN is_adjusting_entry INTEGER NOT NULL DEFAULT 0;

ALTER TABLE ledger_transactions
ADD COLUMN adjusting_reason_code TEXT;

ALTER TABLE approval_proposals
ADD COLUMN matched_rule_id TEXT REFERENCES policy_rules(rule_id);

ALTER TABLE approval_proposals
ADD COLUMN required_approvals INTEGER NOT NULL DEFAULT 1;

ALTER TABLE approval_decisions
ADD COLUMN approver_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_approval_decisions_distinct_approver
ON approval_decisions (proposal_id, action, approver_id)
WHERE approver_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_accounting_periods_entity_period
ON accounting_periods (entity_id, period_key, status);

CREATE INDEX IF NOT EXISTS idx_policy_rules_active_priority
ON policy_rules (active, priority, rule_id);

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
  AND NEW.is_adjusting_entry = OLD.is_adjusting_entry
  AND NEW.adjusting_reason_code = OLD.adjusting_reason_code
  AND NEW.created_at = OLD.created_at
)
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: ledger_transactions UPDATE not permitted');
END;

-- down
-- DROP INDEX IF EXISTS idx_policy_rules_active_priority;
-- DROP INDEX IF EXISTS idx_accounting_periods_entity_period;
-- DROP INDEX IF EXISTS idx_approval_decisions_distinct_approver;
-- DROP TRIGGER IF EXISTS trg_accounting_periods_set_updated_at;
-- DROP TABLE IF EXISTS policy_rules;
-- DROP TABLE IF EXISTS accounting_periods;
