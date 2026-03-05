# Project Documentation Index

## Project Overview

- **Type:** monolith backend service
- **Primary Language:** Python
- **Architecture:** domain-first modular monolith

## Quick Reference

- **Tech Stack:** Python, FastAPI, Pydantic, SQLite (WAL), Pytest
- **Entry Points:** `src/capital_os/main.py`, `src/capital_os/api/app.py`, `src/capital_os/cli/main.py`
- **Core Execution Path:** `runtime/execute_tool.py` -> `tools/*` -> `domain/*` -> `db/session`

## Generated Documentation

- [Project Overview](./project-overview.md)
- [Architecture](./architecture.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Component Inventory](./component-inventory.md)
- [Development Guide](./development-guide.md)
- [Deployment Guide](./deployment-guide.md)
- [Contribution Guide](./contribution-guide.md)
- [API Contracts](./api-contracts.md)
- [Data Models](./data-models.md)
- [Comprehensive Analysis](./comprehensive-analysis-core.md)
- [Project Structure](./project-structure.md)
- [Project Parts Metadata](./project-parts-metadata.json)
- [Workflow Scan State](./project-scan-report.json)

## Existing Documentation

- [Repository README](../README.md)
- [Repository Architecture](../ARCHITECTURE.md)
- [Docs Home](./README.md)
- [Current State](./current-state.md)
- [Tool Reference](./tool-reference.md)
- [Legacy Data Model](./data-model.md)
- [Testing Matrix](./testing-matrix.md)
- [Traceability Matrix](./traceability-matrix.md)
- [Development Workflow](./development-workflow.md)
- [Backlog PRD Closure](./backlog-phase1-prd-closure.md)
- [Backlog Delta 0215](./backlog-phase1-delta-0215.md)
- [MVP Bootstrap Agent Testing](./mvp-bootstrap-agent-testing.md)
- [Docker MCP Integration](./docker-mcp-integration.md)
- [ADR 001 SQLite Canonical Ledger Store](./adr/ADR-001-sqlite-canonical-ledger-store.md)
- [Agent Playbooks Home](./agent-playbooks/README.md)
- [Agent Playbook: Docs Maintenance](./agent-playbooks/docs-maintenance.md)
- [Agent Playbook: Story Execution](./agent-playbooks/story-execution.md)

## Getting Started

1. Read [Project Overview](./project-overview.md).
2. Read [Architecture](./architecture.md) and [Source Tree Analysis](./source-tree-analysis.md).
3. Use [API Contracts](./api-contracts.md) and [Data Models](./data-models.md) when implementing tool or schema changes.
4. Follow [Development Guide](./development-guide.md) for local setup, test, and runtime commands.
