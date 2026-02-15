-- up
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS approval_proposals (
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
  UNIQUE (tool_name, source_system, external_id)
);

CREATE TABLE IF NOT EXISTS approval_decisions (
  decision_id TEXT PRIMARY KEY,
  proposal_id TEXT NOT NULL REFERENCES approval_proposals(proposal_id),
  action TEXT NOT NULL CHECK (action IN ('approve','reject')),
  correlation_id TEXT NOT NULL,
  reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS trg_approval_proposals_set_updated_at
AFTER UPDATE ON approval_proposals
FOR EACH ROW
BEGIN
  UPDATE approval_proposals
  SET updated_at = CURRENT_TIMESTAMP
  WHERE proposal_id = NEW.proposal_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_approval_proposals_append_only_delete
BEFORE DELETE ON approval_proposals
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: approval_proposals DELETE not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_approval_decisions_append_only_update
BEFORE UPDATE ON approval_decisions
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: approval_decisions UPDATE not permitted');
END;

CREATE TRIGGER IF NOT EXISTS trg_approval_decisions_append_only_delete
BEFORE DELETE ON approval_decisions
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: approval_decisions DELETE not permitted');
END;

-- down
-- DROP TRIGGER IF EXISTS trg_approval_proposals_set_updated_at;
-- DROP TRIGGER IF EXISTS trg_approval_proposals_append_only_delete;
-- DROP TRIGGER IF EXISTS trg_approval_decisions_append_only_update;
-- DROP TRIGGER IF EXISTS trg_approval_decisions_append_only_delete;
-- DROP TABLE IF EXISTS approval_decisions;
-- DROP TABLE IF EXISTS approval_proposals;
