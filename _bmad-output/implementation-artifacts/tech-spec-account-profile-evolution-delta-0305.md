---
title: 'Account Profile Evolution Delta (0305)'
slug: 'account-profile-evolution-delta-0305'
created: '2026-03-05T00:00:00Z'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Python'
  - 'FastAPI'
  - 'SQLite (file-backed, WAL)'
  - 'Pytest'
---

# Tech-Spec: Account Profile Evolution Delta

## Overview

This delta introduces a standard account-profile mutation path so operators can rename accounts and accommodate institution suffix/reference changes without violating ledger immutability.

The design keeps `account_id` immutable, routes all writes through the existing tool boundary, and stores external identifier/suffix changes in append-only history for auditability.

## Functional Changes

### New Write Tool
- `update_account_profile`
  - Supports routine single-account profile updates (including `display_name`).
  - Uses existing write-tool contracts: schema validation, deterministic hashing, event logging, auth/authz, and correlation enforcement.
  - Idempotent by `(source_system, external_id)`.

### Identifier/Suffix Evolution
- Add append-only history table for externally meaningful identifier changes:
  - `account_identifier_history`
  - stores `account_id`, source context, identifier value/suffix, `valid_from`, `valid_to`, change reason/context
- On identifier change:
  - close current active row (`valid_to`)
  - insert new active row (`valid_from`)
- On no identifier change:
  - no new history row

### Read Behavior
- No new read tool in this slice.
- Rename/history inspection is performed via direct SQL.

## Invariants and Safety

- Never mutate `account_id`.
- Never rewrite transactions/postings when account profile or suffix changes.
- Write + event log must commit atomically; fail closed on log failure.
- Deterministic output and hash behavior remains required for retries/replay.

## Architecture Changes

### API Layer
- Register `update_account_profile` in `TOOL_HANDLERS` and `WRITE_TOOLS`.
- Enforce standard write capability (`tools:write`) and `x-correlation-id`.

### Domain Layer
- Add account profile update service that:
  - validates account existence
  - validates at least one mutable field supplied
  - applies profile mutation
  - handles optional identifier-history transition logic
  - computes hashes and writes structured event log in one transaction

### Data Layer
- Add migration for `account_identifier_history` with indexes on:
  - `account_id`
  - active row lookup (`account_id`, `valid_to IS NULL` pattern)
- Provide explicit rollback migration path per project standards.

## Proposed Tool Contract

### Input (conceptual)
- `account_id: str`
- `display_name?: str`
- `institution_name?: str`
- `institution_suffix?: str`
- `source_system: str`
- `external_id: str`
- `correlation_id: str`

### Output (conceptual)
- `account_id: str`
- updated profile fields
- `status: "committed"`
- `correlation_id: str`
- `output_hash: str`

## Error Semantics

- `422`: schema/validation errors (missing required fields, empty mutable payload, type violations)
- `400`: domain errors (account not found)
- `401/403`: authn/authz failures (unchanged platform behavior)

## Testing Plan

- Integration tests:
  - happy-path rename/profile update
  - account-not-found
  - empty mutable payload
  - authn/authz/correlation enforcement
  - identifier change writes history row with validity transition
  - event-log fail-closed rollback behavior
- Replay tests:
  - identical state/input => identical `output_hash`
  - duplicate idempotency key returns canonical output
- Concurrency tests:
  - concurrent duplicate updates resolve to one canonical idempotent result

## Backlog Mapping

- Epic 18: Account Profile and Identifier Evolution
  - Story 18.1: Standard `update_account_profile` Tool
  - Story 18.2: Account Identifier History and Suffix Changes
  - Story 18.3: Security, Determinism, and Documentation Hardening
