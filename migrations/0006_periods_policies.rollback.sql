PRAGMA foreign_keys = OFF;

DROP INDEX IF EXISTS idx_policy_rules_active_priority;
DROP INDEX IF EXISTS idx_accounting_periods_entity_period;
DROP INDEX IF EXISTS idx_approval_decisions_distinct_approver;
DROP TRIGGER IF EXISTS trg_accounting_periods_set_updated_at;
DROP TABLE IF EXISTS policy_rules;
DROP TABLE IF EXISTS accounting_periods;

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

ALTER TABLE ledger_transactions RENAME TO ledger_transactions_v6;
CREATE TABLE ledger_transactions (
  transaction_id TEXT PRIMARY KEY,
  source_system TEXT NOT NULL,
  external_id TEXT NOT NULL,
  transaction_date TEXT NOT NULL,
  description TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output_hash TEXT,
  response_payload TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  entity_id TEXT NOT NULL DEFAULT 'entity-default' REFERENCES entities(entity_id),
  UNIQUE (source_system, external_id)
);
INSERT INTO ledger_transactions (
  transaction_id, source_system, external_id, transaction_date, description,
  correlation_id, input_hash, output_hash, response_payload, created_at, entity_id
)
SELECT
  transaction_id, source_system, external_id, transaction_date, description,
  correlation_id, input_hash, output_hash, response_payload, created_at, entity_id
FROM ledger_transactions_v6;
DROP TABLE ledger_transactions_v6;

DROP TRIGGER IF EXISTS trg_ledger_transactions_append_only_delete;
CREATE TRIGGER trg_ledger_transactions_append_only_delete
BEFORE DELETE ON ledger_transactions
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: ledger_transactions DELETE not permitted');
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

ALTER TABLE approval_proposals RENAME TO approval_proposals_v6;
CREATE TABLE approval_proposals (
  proposal_id TEXT PRIMARY KEY,
  tool_name TEXT NOT NULL,
  source_system TEXT NOT NULL,
  external_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  policy_threshold_amount NUMERIC NOT NULL,
  impact_amount NUMERIC NOT NULL,
  request_payload TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('proposed','rejected','committed')),
  decision_reason TEXT,
  approved_transaction_id TEXT REFERENCES ledger_transactions(transaction_id),
  response_payload TEXT,
  output_hash TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  entity_id TEXT NOT NULL DEFAULT 'entity-default' REFERENCES entities(entity_id),
  UNIQUE (tool_name, source_system, external_id)
);
INSERT INTO approval_proposals (
  proposal_id, tool_name, source_system, external_id, correlation_id,
  input_hash, policy_threshold_amount, impact_amount, request_payload, status,
  decision_reason, approved_transaction_id, response_payload, output_hash,
  created_at, updated_at, entity_id
)
SELECT
  proposal_id, tool_name, source_system, external_id, correlation_id,
  input_hash, policy_threshold_amount, impact_amount, request_payload, status,
  decision_reason, approved_transaction_id, response_payload, output_hash,
  created_at, updated_at, entity_id
FROM approval_proposals_v6;
DROP TABLE approval_proposals_v6;

ALTER TABLE approval_decisions RENAME TO approval_decisions_v6;
CREATE TABLE approval_decisions (
  decision_id TEXT PRIMARY KEY,
  proposal_id TEXT NOT NULL REFERENCES approval_proposals(proposal_id),
  action TEXT NOT NULL CHECK (action IN ('approve','reject')),
  correlation_id TEXT NOT NULL,
  reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO approval_decisions (
  decision_id, proposal_id, action, correlation_id, reason, created_at
)
SELECT
  decision_id, proposal_id, action, correlation_id, reason, created_at
FROM approval_decisions_v6;
DROP TABLE approval_decisions_v6;

DROP TRIGGER IF EXISTS trg_approval_proposals_set_updated_at;
CREATE TRIGGER IF NOT EXISTS trg_approval_proposals_set_updated_at
AFTER UPDATE ON approval_proposals
FOR EACH ROW
BEGIN
  UPDATE approval_proposals
  SET updated_at = CURRENT_TIMESTAMP
  WHERE proposal_id = NEW.proposal_id;
END;

DROP TRIGGER IF EXISTS trg_approval_proposals_append_only_delete;
CREATE TRIGGER IF NOT EXISTS trg_approval_proposals_append_only_delete
BEFORE DELETE ON approval_proposals
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: approval_proposals DELETE not permitted');
END;

DROP TRIGGER IF EXISTS trg_approval_proposals_entity_id_immutable;
CREATE TRIGGER IF NOT EXISTS trg_approval_proposals_entity_id_immutable
BEFORE UPDATE OF entity_id ON approval_proposals
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'approval_proposals.entity_id is immutable');
END;

DROP TRIGGER IF EXISTS trg_approval_decisions_append_only_update;
CREATE TRIGGER IF NOT EXISTS trg_approval_decisions_append_only_update
BEFORE UPDATE ON approval_decisions
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: approval_decisions UPDATE not permitted');
END;

DROP TRIGGER IF EXISTS trg_approval_decisions_append_only_delete;
CREATE TRIGGER IF NOT EXISTS trg_approval_decisions_append_only_delete
BEFORE DELETE ON approval_decisions
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: approval_decisions DELETE not permitted');
END;

PRAGMA foreign_keys = ON;
