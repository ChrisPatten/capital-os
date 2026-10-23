-- up
PRAGMA foreign_keys = ON;

-- Versioned budget lines. A change inserts a new row and deactivates the previous active
-- version for the same item_key; history is never edited or deleted.
CREATE TABLE IF NOT EXISTS budget_items (
  item_id TEXT PRIMARY KEY,
  item_key TEXT NOT NULL,
  name TEXT NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('inflow','outflow')),
  amount NUMERIC NOT NULL CHECK (amount >= 0),
  cadence TEXT NOT NULL CHECK (cadence IN ('monthly','biweekly','quarterly','annual')),
  day_of_month INTEGER CHECK (day_of_month BETWEEN 1 AND 31),
  anchor_date TEXT,
  account_id TEXT REFERENCES accounts(account_id),
  bucket TEXT CHECK (bucket IN ('recurring','debt','discretionary','savings','annual')),
  active INTEGER NOT NULL DEFAULT 1,
  effective_date TEXT NOT NULL,
  source TEXT,
  metadata TEXT NOT NULL DEFAULT '{}',
  entity_id TEXT NOT NULL DEFAULT 'entity-default' REFERENCES entities(entity_id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (direction = 'outflow' AND bucket IS NOT NULL)
    OR (direction = 'inflow' AND bucket IS NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_budget_items_active_key
ON budget_items (item_key)
WHERE active = 1;

CREATE INDEX IF NOT EXISTS idx_budget_items_list
ON budget_items (active, item_key, effective_date, item_id);

CREATE TRIGGER IF NOT EXISTS budget_items_versioned_update_guard
BEFORE UPDATE ON budget_items
FOR EACH ROW
WHEN (
  OLD.item_id IS NOT NEW.item_id
  OR OLD.item_key IS NOT NEW.item_key
  OR OLD.name IS NOT NEW.name
  OR OLD.direction IS NOT NEW.direction
  OR OLD.amount IS NOT NEW.amount
  OR OLD.cadence IS NOT NEW.cadence
  OR OLD.day_of_month IS NOT NEW.day_of_month
  OR OLD.anchor_date IS NOT NEW.anchor_date
  OR OLD.account_id IS NOT NEW.account_id
  OR OLD.bucket IS NOT NEW.bucket
  OR OLD.effective_date IS NOT NEW.effective_date
  OR OLD.source IS NOT NEW.source
  OR OLD.metadata IS NOT NEW.metadata
  OR OLD.entity_id IS NOT NEW.entity_id
  OR OLD.created_at IS NOT NEW.created_at
  OR (OLD.active = 0 AND NEW.active <> 0)
)
BEGIN
  SELECT RAISE(ABORT, 'Versioned table: budget_items UPDATE not permitted except deactivation');
END;

CREATE TRIGGER IF NOT EXISTS budget_items_no_delete
BEFORE DELETE ON budget_items
FOR EACH ROW
BEGIN
  SELECT RAISE(ABORT, 'Append-only table: budget_items DELETE not permitted');
END;

-- down
-- DROP TRIGGER IF EXISTS budget_items_no_delete;
-- DROP TRIGGER IF EXISTS budget_items_versioned_update_guard;
-- DROP INDEX IF EXISTS idx_budget_items_list;
-- DROP INDEX IF EXISTS idx_budget_items_active_key;
-- DROP TABLE IF EXISTS budget_items;
