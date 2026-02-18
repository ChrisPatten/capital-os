#!/bin/bash
set -e

DB_PATH="${CAPITAL_OS_DB_PATH:-/app/data/capital_os.db}"

# Init DB if missing
if [ ! -f "$DB_PATH" ]; then
  python3 scripts/apply_migrations.py
  python3 scripts/import_coa.py config/coa.yaml
fi

# Start Capital OS in background (redirect logs to stderr to keep stdout clean for MCP)
CAPITAL_OS_DB_URL="${CAPITAL_OS_DB_URL:-sqlite:///./data/capital_os.db}" \
  uvicorn capital_os.api.app:app --host 127.0.0.1 --port 8000 >&2 &

# Wait for health (up to 15s)
for i in $(seq 1 30); do
  curl -sf http://127.0.0.1:8000/health >/dev/null && break || sleep 0.5
done

# Run MCP server (stdio)
exec python3 mcp/server.py
