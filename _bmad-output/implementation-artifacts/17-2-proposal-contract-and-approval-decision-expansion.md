# Story 17.2: Proposal Contract and Approval Decision Expansion

Status: ready-for-dev

## Story

As a family-office AI operator,  
I want duplicate-risk proposals to return complete side-by-side transaction context,  
so that approval decisions are informed, auditable, and consistent with existing proposal/approval behavior.

## Acceptance Criteria

1. Duplicate-risk-triggered `record_transaction_bundle` proposal response includes:
  - `proposed_transaction`
  - `matched_transactions[]` (all candidates)
  - `match_reason: "same_account_date_amount"`
2. Response payload shape is schema-validated and deterministic for identical state + input.
3. Existing proposal status contract is preserved (`status="proposed"`, no immediate commit).
4. Existing approval decision flow is preserved:
  - one decision per proposed transaction
  - `approve_proposed_transaction` commits exactly once
  - `reject_proposed_transaction` remains non-mutating
5. Duplicate-risk proposal payload is persisted for canonical replay and stable `output_hash`.
6. Approval response behavior remains backward-compatible for existing clients that rely on current committed/proposed fields.
7. Event logs capture proposal and decision paths with deterministic `input_hash`/`output_hash` and correlation IDs.

## Tasks / Subtasks

- [ ] Task 1: Extend response schemas for duplicate-risk context (AC: 1, 2, 6)
  - [ ] Update `RecordTransactionBundleOut` in `src/capital_os/schemas/tools.py` with optional duplicate-risk proposal fields.
  - [ ] Define strict nested models for `proposed_transaction` and `matched_transactions[]`.
  - [ ] Ensure unknown keys are rejected and canonical serialization is preserved.
- [ ] Task 2: Expand proposal payload construction/persistence (AC: 1, 2, 3, 5)
  - [ ] Update proposal response builder in `src/capital_os/domain/ledger/service.py` to include duplicate-risk context when triggered.
  - [ ] Persist expanded response payload via existing proposal persistence path.
  - [ ] Ensure deterministic ordering of matched transaction list.
- [ ] Task 3: Preserve approval service semantics (AC: 4, 6)
  - [ ] Verify `approve_proposed_transaction` and `reject_proposed_transaction` remain unchanged in decision semantics.
  - [ ] Ensure proposal replay after commit/reject remains canonical and deterministic.
- [ ] Task 4: Add integration/replay coverage for contract behavior (AC: 1–7)
  - [ ] Integration: proposal response includes full duplicate-risk context fields.
  - [ ] Integration: approve commits once; repeat approvals replay canonical result.
  - [ ] Integration: reject remains non-mutating and idempotent.
  - [ ] Replay: duplicate-risk proposal payload and output hash are reproducible.
  - [ ] Contract validation: response shape stays backward-compatible for existing clients.

## Dev Notes

### Product Decisions Locked for This Story

- Duplicate-risk match criteria are exact (`account_id + effective_date + amount` normalized to 4dp).
- All candidate matches are returned for a single proposed transaction.
- Approval authority remains any writer.
- No global write lock is introduced; proposals are per transaction.

### Contract Strategy

- Add fields as optional extensions to avoid breaking existing consumers.
- Keep top-level status semantics unchanged (`committed`, `idempotent-replay`, `proposed`, `rejected`).
- Keep deterministic hashing over canonicalized response payloads.

### Suggested File Touchpoints

- `src/capital_os/schemas/tools.py`
- `src/capital_os/domain/ledger/service.py`
- `src/capital_os/domain/approval/service.py` (verification only; modify only if required)
- `tests/integration/test_approval_workflow.py`
- `tests/integration/test_tool_contract_validation.py`
- `tests/replay/test_output_replay.py`

### References

- [Source: `_bmad-output/planning-artifacts/epic-17-duplicate-risk-approval-gate.md`]
- [Source: `_bmad-output/implementation-artifacts/17-1-duplicate-risk-detection-rule-in-write-path.md`]
- [Source: `_bmad-output/planning-artifacts/epic-4-approval-gates.md`]
- [Source: `CONSTITUTION.md`]
