# Capital OS Phase 1

Set DB URL (SQLite):

```bash
export CAPITAL_OS_DB_URL=sqlite:///./data/capital_os.db
```

Run API:

```bash
uvicorn capital_os.main:app --reload
```
