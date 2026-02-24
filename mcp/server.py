#!/usr/bin/env python3
"""MCP server for Capital OS — proxies all 25 tools to the local FastAPI instance."""
from __future__ import annotations

import asyncio
import copy
import json
import os
import uuid

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ---------------------------------------------------------------------------
# Import Pydantic schemas (source of truth for tool contracts)
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from capital_os.schemas.tools import (  # noqa: E402
    AnalyzeDebtIn,
    ApproveConfigChangeIn,
    ApproveProposedTransactionIn,
    ClosePeriodIn,
    ComputeCapitalPostureIn,
    ComputeConsolidatedPostureIn,
    CreateAccountIn,
    CreateOrUpdateObligationIn,
    FulfillObligationIn,
    GetAccountBalancesIn,
    GetAccountTreeIn,
    GetConfigIn,
    GetProposalIn,
    GetTransactionByExternalIdIn,
    ListAccountsIn,
    ListObligationsIn,
    ListProposalsIn,
    ListTransactionsIn,
    LockPeriodIn,
    ProposeConfigChangeIn,
    ReconcileAccountIn,
    RecordBalanceSnapshotIn,
    RecordTransactionBundleIn,
    RejectProposedTransactionIn,
    SimulateSpendIn,
    UpdateAccountMetadataIn,
)

# ---------------------------------------------------------------------------
# Tool registry: name -> (schema_class, description)
# ---------------------------------------------------------------------------
_TOOL_REGISTRY: list[tuple[str, type, str]] = [
    ("create_account", CreateAccountIn, "Create a new account in the chart of accounts"),
    ("update_account_metadata", UpdateAccountMetadataIn, "Update metadata on an existing account"),
    ("list_accounts", ListAccountsIn, "List accounts with cursor-based pagination"),
    ("get_account_tree", GetAccountTreeIn, "Retrieve the account hierarchy as a tree"),
    ("get_account_balances", GetAccountBalancesIn, "Get balances for all accounts as of a given date"),
    ("record_transaction_bundle", RecordTransactionBundleIn, "Record a double-entry transaction bundle (idempotent)"),
    ("list_transactions", ListTransactionsIn, "List committed transactions with cursor-based pagination"),
    ("get_transaction_by_external_id", GetTransactionByExternalIdIn, "Look up a transaction by source_system + external_id"),
    ("record_balance_snapshot", RecordBalanceSnapshotIn, "Record an external balance snapshot for an account"),
    ("reconcile_account", ReconcileAccountIn, "Reconcile ledger vs snapshot balance for an account"),
    ("create_or_update_obligation", CreateOrUpdateObligationIn, "Create or update a recurring financial obligation"),
    ("fulfill_obligation", FulfillObligationIn, "Mark an obligation as fulfilled (deactivate) and optionally link the payment transaction"),
    ("list_obligations", ListObligationsIn, "List obligations with cursor-based pagination"),
    ("list_proposals", ListProposalsIn, "List approval proposals with optional status filter"),
    ("get_proposal", GetProposalIn, "Retrieve full details of a specific approval proposal"),
    ("approve_proposed_transaction", ApproveProposedTransactionIn, "Approve a pending transaction proposal"),
    ("reject_proposed_transaction", RejectProposedTransactionIn, "Reject a pending transaction proposal"),
    ("get_config", GetConfigIn, "Retrieve current runtime config and policy rules"),
    ("propose_config_change", ProposeConfigChangeIn, "Propose a change to runtime settings or policy rules"),
    ("approve_config_change", ApproveConfigChangeIn, "Approve a pending config change proposal"),
    ("close_period", ClosePeriodIn, "Close an accounting period (prevents new transactions)"),
    ("lock_period", LockPeriodIn, "Lock a closed period (prevents all modifications)"),
    ("compute_capital_posture", ComputeCapitalPostureIn, "Compute capital posture and risk band from liquidity inputs"),
    ("compute_consolidated_posture", ComputeConsolidatedPostureIn, "Compute consolidated posture across multiple entities"),
    ("simulate_spend", SimulateSpendIn, "Simulate future liquidity under a given spend plan"),
    ("analyze_debt", AnalyzeDebtIn, "Rank and analyze liabilities for optimal payoff strategy"),
]


def _strip_correlation_id(schema: dict) -> dict:
    """Remove correlation_id from a JSON schema (it's auto-generated per call)."""
    schema = copy.deepcopy(schema)
    props = schema.get("properties", {})
    props.pop("correlation_id", None)
    required = schema.get("required", [])
    if "correlation_id" in required:
        schema["required"] = [r for r in required if r != "correlation_id"]
    return schema


def _build_tools() -> list[types.Tool]:
    tools = []
    for name, model_cls, description in _TOOL_REGISTRY:
        raw_schema = model_cls.model_json_schema()
        schema = _strip_correlation_id(raw_schema)
        # Remove title — MCP clients don't need it
        schema.pop("title", None)
        tools.append(
            types.Tool(
                name=name,
                description=description,
                inputSchema=schema,
            )
        )
    return tools


TOOLS = _build_tools()

# ---------------------------------------------------------------------------
# Runtime config
# ---------------------------------------------------------------------------
CAPITAL_OS_BASE_URL = os.environ.get("CAPITAL_OS_BASE_URL", "http://127.0.0.1:8000")
AUTH_TOKEN = os.environ.get("CAPITAL_OS_AUTH_TOKEN", "dev-admin-token")

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
server = Server("capital-os")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    # Validate tool name
    known = {t[0] for t in _TOOL_REGISTRY}
    if name not in known:
        raise ValueError(f"Unknown tool: {name}")

    # Inject correlation_id
    payload = dict(arguments)
    payload["correlation_id"] = str(uuid.uuid4()).replace("-", "")[:32]

    url = f"{CAPITAL_OS_BASE_URL}/tools/{name}"
    headers = {
        "x-capital-auth-token": AUTH_TOKEN,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)

    body = response.json()
    text = json.dumps(body, indent=2, default=str)

    if response.status_code >= 400:
        return [
            types.TextContent(
                type="text",
                text=f"Error {response.status_code}:\n{text}",
            )
        ]

    return [types.TextContent(type="text", text=text)]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
