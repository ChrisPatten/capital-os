from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
import json


BALANCE_SOURCE_POLICIES = {"ledger_only", "snapshot_only", "best_available"}
AUTHN_METHOD_HEADER_TOKEN = "header_token"

DEFAULT_TOKEN_IDENTITIES = {
    "dev-admin-token": {
        "actor_id": "actor-admin",
        "capabilities": ["tools:read", "tools:write", "tools:approve", "tools:admin"],
    },
    "dev-reader-token": {
        "actor_id": "actor-reader",
        "capabilities": ["tools:read"],
    },
}

DEFAULT_TOOL_CAPABILITIES = {
    "record_transaction_bundle": "tools:write",
    "record_balance_snapshot": "tools:write",
    "create_or_update_obligation": "tools:write",
    "compute_capital_posture": "tools:read",
    "simulate_spend": "tools:read",
    "analyze_debt": "tools:read",
    "approve_proposed_transaction": "tools:approve",
    "reject_proposed_transaction": "tools:approve",
    "list_accounts": "tools:read",
    "get_account_tree": "tools:read",
    "get_account_balances": "tools:read",
    "list_transactions": "tools:read",
    "get_transaction_by_external_id": "tools:read",
    "list_obligations": "tools:read",
    "list_proposals": "tools:read",
    "get_proposal": "tools:read",
    "get_config": "tools:read",
    "propose_config_change": "tools:admin",
    "approve_config_change": "tools:admin",
    "reconcile_account": "tools:read",
    "close_period": "tools:write",
    "lock_period": "tools:write",
}


def _normalize_balance_source_policy(raw_value: str) -> str:
    value = raw_value.strip().lower()
    if value not in BALANCE_SOURCE_POLICIES:
        raise ValueError(
            "CAPITAL_OS_BALANCE_SOURCE_POLICY must be one of "
            "ledger_only|snapshot_only|best_available"
        )
    return value


@dataclass(frozen=True)
class Settings:
    app_env: str
    db_url: str
    money_precision: int = 4
    approval_threshold_amount: str = "1000.0000"
    balance_source_policy: str = "best_available"
    token_identities: dict[str, dict[str, object]] | None = None
    tool_capabilities: dict[str, str] | None = None
    no_egress_allowlist: tuple[str, ...] = ()


def _parse_json_mapping(raw_value: str, *, env_name: str) -> dict:
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{env_name} must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{env_name} must be a JSON object")
    return parsed


def _load_token_identities() -> dict[str, dict[str, object]]:
    raw = os.getenv("CAPITAL_OS_AUTH_TOKENS_JSON")
    mapping = _parse_json_mapping(raw, env_name="CAPITAL_OS_AUTH_TOKENS_JSON") if raw else DEFAULT_TOKEN_IDENTITIES
    normalized: dict[str, dict[str, object]] = {}
    for token, identity in mapping.items():
        if not isinstance(token, str) or not token:
            raise ValueError("CAPITAL_OS_AUTH_TOKENS_JSON token keys must be non-empty strings")
        if not isinstance(identity, dict):
            raise ValueError("CAPITAL_OS_AUTH_TOKENS_JSON values must be objects")
        actor_id = identity.get("actor_id")
        capabilities = identity.get("capabilities")
        if not isinstance(actor_id, str) or not actor_id:
            raise ValueError("CAPITAL_OS_AUTH_TOKENS_JSON actor_id must be non-empty string")
        if not isinstance(capabilities, list) or not all(
            isinstance(capability, str) and capability for capability in capabilities
        ):
            raise ValueError("CAPITAL_OS_AUTH_TOKENS_JSON capabilities must be list[str]")
        normalized[token] = {
            "actor_id": actor_id,
            "capabilities": tuple(sorted(set(capabilities))),
        }
    return normalized


def _load_tool_capabilities() -> dict[str, str]:
    raw = os.getenv("CAPITAL_OS_TOOL_CAPABILITIES_JSON")
    mapping = _parse_json_mapping(raw, env_name="CAPITAL_OS_TOOL_CAPABILITIES_JSON") if raw else DEFAULT_TOOL_CAPABILITIES
    normalized: dict[str, str] = {}
    for tool_name, capability in mapping.items():
        if not isinstance(tool_name, str) or not tool_name:
            raise ValueError("CAPITAL_OS_TOOL_CAPABILITIES_JSON keys must be non-empty strings")
        if not isinstance(capability, str) or not capability:
            raise ValueError("CAPITAL_OS_TOOL_CAPABILITIES_JSON values must be non-empty strings")
        normalized[tool_name] = capability
    return normalized


def _load_no_egress_allowlist() -> tuple[str, ...]:
    raw = os.getenv("CAPITAL_OS_EGRESS_ALLOWLIST", "")
    if not raw.strip():
        return ()
    hosts = [host.strip().lower() for host in raw.split(",") if host.strip()]
    return tuple(sorted(set(hosts)))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    db_url = os.getenv("CAPITAL_OS_DB_URL")
    if not db_url:
        db_url = "sqlite:///./data/capital_os.db"

    balance_source_policy = _normalize_balance_source_policy(
        os.getenv("CAPITAL_OS_BALANCE_SOURCE_POLICY", "best_available")
    )

    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        db_url=db_url,
        approval_threshold_amount=os.getenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "1000.0000"),
        balance_source_policy=balance_source_policy,
        token_identities=_load_token_identities(),
        tool_capabilities=_load_tool_capabilities(),
        no_egress_allowlist=_load_no_egress_allowlist(),
    )
