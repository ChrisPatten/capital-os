# Epic 6: Read/Query Surface (FR-13..FR-18, NFR-08)

## Goal
Deliver deterministic read/query tools with stable cursor pagination so agents can operate without direct DB access.

### Story 6.1: Read Query Tooling Foundation
- Add shared deterministic pagination and cursor encoding primitives.
- Implement `list_accounts`, `get_account_tree`, and `get_account_balances`.

### Story 6.2: Transaction and Obligation Query Surface
- Implement `list_transactions`, `get_transaction_by_external_id`, and `list_obligations`.
- Enforce stable sort keys and idempotent repeated query responses.

### Story 6.3: Proposal and Config Query Surface
- Implement `list_proposals`, `get_proposal`, and `get_config`.
- Add `propose_config_change` + `approve_config_change` gating hooks.
