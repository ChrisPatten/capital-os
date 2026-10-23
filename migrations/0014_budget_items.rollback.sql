-- rollback
DROP TRIGGER IF EXISTS budget_items_no_delete;
DROP TRIGGER IF EXISTS budget_items_versioned_update_guard;
DROP INDEX IF EXISTS idx_budget_items_list;
DROP INDEX IF EXISTS idx_budget_items_active_key;
DROP TABLE IF EXISTS budget_items;
