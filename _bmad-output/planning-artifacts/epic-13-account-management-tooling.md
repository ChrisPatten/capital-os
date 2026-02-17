# Epic 13: Account Management Tooling

## Goal
Enable agents to create accounts and update account metadata at runtime through the standard tool API, eliminating the dependency on manual YAML imports for chart of accounts changes.

## Why This Epic Exists
- Agents currently cannot add accounts — the only creation path is `scripts/import_coa.py` from YAML.
- The domain service (`create_account_entry`) exists but is not exposed as a tool endpoint.
- Account metadata cannot be modified at runtime at all.
- Real agent workflows require adding new cash accounts, asset accounts, expense categories, etc. on the fly.
- Agent skill documentation explicitly tells agents NOT to create accounts, which must be corrected.

## Scope Boundaries
- In scope:
  - `create_account` write tool (single account creation per call)
  - `update_account_metadata` write tool (merge-patch semantics)
  - Event logging + deterministic hashing for both tools
  - Agent skill file updates (CLAUDE_SKILL.md, CODEX_SKILL.md, tool-reference.md)
- Out of scope:
  - Batch account creation
  - Account deletion or deactivation
  - Account renaming (code/name changes post-creation)
  - Approval workflow for account creation

## Story 13.1: Create Account Tool

Create a `create_account` tool endpoint following the established tool pattern. Accepts `code`, `name`, `account_type` (required) plus optional `parent_account_id`, `entity_id`, `metadata`. Direct write with `tools:write` capability — no approval workflow.

Acceptance Criteria:
- Schema validation on all required fields (422 on invalid)
- Parent and entity existence validation (400 on missing)
- Duplicate code rejection (400, not silent upsert)
- Cycle rejection via existing DB triggers
- Event-logged with input/output hashing
- Auth/authz enforced (`tools:write` required)
- Agent skill files and tool reference updated

## Story 13.2: Update Account Metadata Tool

Create an `update_account_metadata` tool endpoint using JSON merge-patch semantics. Provided keys overwrite, unmentioned keys preserved, keys set to `null` are removed.

Acceptance Criteria:
- Merge-patch semantics on metadata field
- Account existence validation (400 on missing)
- Event-logged with input/output hashing
- Auth/authz enforced (`tools:write` required)
- Agent skill files and tool reference updated

## Dependencies
- All existing infrastructure is in place (DB schema, triggers, domain service skeleton, tool pattern).
- No dependency on other backlog epics.

## Exit Criteria
1. Agent can create any account type via `POST /tools/create_account`.
2. Agent can update account metadata via `POST /tools/update_account_metadata`.
3. Both tools meet observability, determinism, and security invariants.
4. Agent skill files accurately document the new capabilities.
