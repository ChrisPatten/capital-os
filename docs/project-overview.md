# Project Overview

## Purpose

Capital OS provides a deterministic, auditable financial truth layer built around double-entry accounting and schema-validated tool interfaces.

## Repository Classification

- Repository type: monolith
- Project type: backend service
- Primary language: Python

## Executive Summary

The codebase combines FastAPI and Typer transports with a shared runtime executor that enforces validation, transaction boundaries, deterministic hashing, and structured event logging. SQLite (WAL mode) is the canonical data store and is managed through numbered SQL migrations with paired rollback scripts.

## High-Level Capabilities

- Ledger transaction recording with balancing invariants and idempotency controls.
- Balance snapshot and obligation lifecycle tooling.
- Approval and governance controls for selected write operations.
- Query/read surface with replay determinism and security boundary tests.
- Authn/authz-protected HTTP tool invocation plus trusted local CLI invocation.

## Primary References

- [Architecture](./architecture.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Development Guide](./development-guide.md)
- [API Contracts](./api-contracts.md)
- [Data Models](./data-models.md)
