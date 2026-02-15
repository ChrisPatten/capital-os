DROP TRIGGER IF EXISTS trg_approval_proposals_set_updated_at;
DROP TRIGGER IF EXISTS trg_approval_proposals_append_only_delete;
DROP TRIGGER IF EXISTS trg_approval_decisions_append_only_update;
DROP TRIGGER IF EXISTS trg_approval_decisions_append_only_delete;
DROP TABLE IF EXISTS approval_decisions;
DROP TABLE IF EXISTS approval_proposals;
