from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from capital_os.db.session import transaction


VALID_ACCOUNT_TYPES = {"ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"}
DEFAULT_ALLOW_UPDATES = {
    "name": True,
    "description": True,
    "metadata": True,
    "is_active": True,
    "parent_id": True,
}


class CoaImportError(ValueError):
    pass


@dataclass(frozen=True)
class CoaImportSummary:
    created: int
    updated: int
    unchanged: int
    warnings: tuple[str, ...]


def load_coa_yaml(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)
    if not isinstance(parsed, dict):
        raise CoaImportError("COA file must be a YAML object")
    return parsed


def validate_coa_payload(payload: dict[str, Any]) -> None:
    version = payload.get("version")
    if not isinstance(version, int):
        raise CoaImportError("version is required and must be an integer")
    if version != 1:
        raise CoaImportError("version must be 1")

    accounts = payload.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        raise CoaImportError("accounts is required and must be a non-empty list")

    account_ids: set[str] = set()
    parent_refs: dict[str, str] = {}
    for idx, account in enumerate(accounts):
        if not isinstance(account, dict):
            raise CoaImportError(f"accounts[{idx}] must be an object")

        account_id = account.get("account_id")
        if not isinstance(account_id, str) or not account_id or any(ch.isspace() for ch in account_id):
            raise CoaImportError(f"accounts[{idx}].account_id must be a non-empty string without spaces")
        if account_id in account_ids:
            raise CoaImportError(f"duplicate account_id: {account_id}")
        account_ids.add(account_id)

        name = account.get("name")
        if not isinstance(name, str) or not name:
            raise CoaImportError(f"accounts[{idx}].name is required and must be a non-empty string")

        account_type = account.get("type")
        if not isinstance(account_type, str) or account_type not in VALID_ACCOUNT_TYPES:
            raise CoaImportError(
                f"accounts[{idx}].type must be one of: {', '.join(sorted(VALID_ACCOUNT_TYPES))}"
            )

        parent_id = account.get("parent_id")
        if parent_id is not None and not isinstance(parent_id, str):
            raise CoaImportError(f"accounts[{idx}].parent_id must be string or null")
        if isinstance(parent_id, str):
            parent_refs[account_id] = parent_id

        if "is_active" in account and not isinstance(account["is_active"], bool):
            raise CoaImportError(f"accounts[{idx}].is_active must be boolean when present")
        if "currency" in account and not isinstance(account["currency"], str):
            raise CoaImportError(f"accounts[{idx}].currency must be string when present")
        if "description" in account and not isinstance(account["description"], str):
            raise CoaImportError(f"accounts[{idx}].description must be string when present")
        if "metadata" in account and not isinstance(account["metadata"], dict):
            raise CoaImportError(f"accounts[{idx}].metadata must be object/map when present")
        if "tags" in account:
            tags = account["tags"]
            if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                raise CoaImportError(f"accounts[{idx}].tags must be list[str] when present")
        if "external_refs" in account:
            external_refs = account["external_refs"]
            if not isinstance(external_refs, list):
                raise CoaImportError(f"accounts[{idx}].external_refs must be a list when present")
            for ref_idx, ext in enumerate(external_refs):
                if not isinstance(ext, dict):
                    raise CoaImportError(f"accounts[{idx}].external_refs[{ref_idx}] must be an object")
                if not isinstance(ext.get("system"), str) or not isinstance(ext.get("ref"), str):
                    raise CoaImportError(
                        f"accounts[{idx}].external_refs[{ref_idx}] must contain string system/ref"
                    )

    for account_id, parent_id in parent_refs.items():
        if parent_id not in account_ids:
            raise CoaImportError(f"account_id '{account_id}' has unknown parent_id '{parent_id}'")

    _assert_acyclic(parent_refs)

    groups = payload.get("groups")
    if groups is not None:
        if not isinstance(groups, list):
            raise CoaImportError("groups must be a list when present")
        group_ids: set[str] = set()
        for idx, group in enumerate(groups):
            if not isinstance(group, dict):
                raise CoaImportError(f"groups[{idx}] must be an object")
            group_id = group.get("group_id")
            if not isinstance(group_id, str) or not group_id:
                raise CoaImportError(f"groups[{idx}].group_id must be a non-empty string")
            if group_id in group_ids:
                raise CoaImportError(f"duplicate group_id: {group_id}")
            group_ids.add(group_id)
            group_account_ids = group.get("account_ids", [])
            if not isinstance(group_account_ids, list):
                raise CoaImportError(f"groups[{idx}].account_ids must be a list when present")
            for ref in group_account_ids:
                if not isinstance(ref, str) or ref not in account_ids:
                    raise CoaImportError(f"groups[{idx}] references unknown account_id '{ref}'")

    aliases = payload.get("aliases")
    if aliases is not None:
        if not isinstance(aliases, list):
            raise CoaImportError("aliases must be a list when present")
        alias_values: set[str] = set()
        for idx, alias_item in enumerate(aliases):
            if not isinstance(alias_item, dict):
                raise CoaImportError(f"aliases[{idx}] must be an object")
            alias = alias_item.get("alias")
            account_id = alias_item.get("account_id")
            if not isinstance(alias, str) or not alias:
                raise CoaImportError(f"aliases[{idx}].alias must be a non-empty string")
            if alias in alias_values:
                raise CoaImportError(f"duplicate alias: {alias}")
            alias_values.add(alias)
            if not isinstance(account_id, str) or account_id not in account_ids:
                raise CoaImportError(f"aliases[{idx}] references unknown account_id '{account_id}'")


def import_coa_payload(payload: dict[str, Any], *, dry_run: bool = False) -> CoaImportSummary:
    validate_coa_payload(payload)

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    default_currency = metadata.get("currency") if isinstance(metadata.get("currency"), str) else None

    import_policy = payload.get("import_policy") if isinstance(payload.get("import_policy"), dict) else {}
    mode = str(import_policy.get("mode", "upsert")).strip().lower()
    if mode not in {"upsert", "create_only"}:
        raise CoaImportError("import_policy.mode must be upsert or create_only")
    allow_updates = dict(DEFAULT_ALLOW_UPDATES)
    raw_allow_updates = import_policy.get("allow_updates")
    if isinstance(raw_allow_updates, dict):
        for key in DEFAULT_ALLOW_UPDATES:
            if key in raw_allow_updates:
                allow_updates[key] = bool(raw_allow_updates[key])

    accounts = payload["accounts"]
    warnings: list[str] = []
    created = 0
    updated = 0
    unchanged = 0

    with transaction() as conn:
        existing_rows = conn.execute("SELECT account_id FROM accounts").fetchall()
        existing_ids = {str(row["account_id"]) for row in existing_rows}

        for account in accounts:
            account_id = account["account_id"]
            parent_id = account.get("parent_id")
            account_type = account["type"].lower()

            metadata_payload = _build_metadata(account, default_currency)
            metadata_json = json.dumps(metadata_payload, separators=(",", ":"), sort_keys=True)

            if account_id not in existing_ids:
                created += 1
                if not dry_run:
                    conn.execute(
                        """
                        INSERT INTO accounts (account_id, code, name, account_type, parent_account_id, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (account_id, account_id, account["name"], account_type, parent_id, metadata_json),
                    )
                continue

            if mode == "create_only":
                unchanged += 1
                continue

            row = conn.execute(
                """
                SELECT name, parent_account_id, metadata
                FROM accounts
                WHERE account_id = ?
                """,
                (account_id,),
            ).fetchone()
            if row is None:
                unchanged += 1
                continue

            current_name = str(row["name"])
            current_parent_id = row["parent_account_id"]
            current_metadata = row["metadata"] if row["metadata"] else "{}"

            next_name = account["name"] if allow_updates["name"] else current_name
            next_parent_id = parent_id if allow_updates["parent_id"] else current_parent_id
            next_metadata = _merge_metadata(
                existing_metadata_raw=current_metadata,
                incoming_metadata=metadata_payload,
                allow_description=allow_updates["description"],
                allow_metadata=allow_updates["metadata"],
                allow_is_active=allow_updates["is_active"],
            )
            next_metadata_json = json.dumps(next_metadata, separators=(",", ":"), sort_keys=True)

            if (
                next_name == current_name
                and next_parent_id == current_parent_id
                and next_metadata_json == current_metadata
            ):
                unchanged += 1
                continue

            updated += 1
            if not dry_run:
                conn.execute(
                    """
                    UPDATE accounts
                    SET name = ?, parent_account_id = ?, metadata = ?
                    WHERE account_id = ?
                    """,
                    (next_name, next_parent_id, next_metadata_json, account_id),
                )

        if import_policy.get("forbid_deletes", True):
            file_ids = {account["account_id"] for account in accounts}
            extra_ids = sorted(existing_ids - file_ids)
            if extra_ids:
                warnings.append(f"db has {len(extra_ids)} accounts not present in COA file")

        if dry_run:
            conn.rollback()

    return CoaImportSummary(
        created=created,
        updated=updated,
        unchanged=unchanged,
        warnings=tuple(warnings),
    )


def import_coa_file(path: str | Path, *, dry_run: bool = False) -> CoaImportSummary:
    payload = load_coa_yaml(path)
    return import_coa_payload(payload, dry_run=dry_run)


def validate_coa_file(path: str | Path) -> None:
    payload = load_coa_yaml(path)
    validate_coa_payload(payload)


def _build_metadata(account: dict[str, Any], default_currency: str | None) -> dict[str, Any]:
    raw_metadata = account.get("metadata")
    metadata: dict[str, Any] = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}

    if "description" in account:
        metadata["description"] = account.get("description")
    if "is_active" in account:
        metadata["is_active"] = bool(account["is_active"])
    else:
        metadata.setdefault("is_active", True)

    currency = account.get("currency", default_currency)
    if isinstance(currency, str) and currency:
        metadata["currency"] = currency

    if isinstance(account.get("external_refs"), list):
        metadata["external_refs"] = account["external_refs"]
    if isinstance(account.get("tags"), list):
        metadata["tags"] = account["tags"]
    return metadata


def _merge_metadata(
    *,
    existing_metadata_raw: str,
    incoming_metadata: dict[str, Any],
    allow_description: bool,
    allow_metadata: bool,
    allow_is_active: bool,
) -> dict[str, Any]:
    try:
        existing_metadata = json.loads(existing_metadata_raw) if existing_metadata_raw else {}
        if not isinstance(existing_metadata, dict):
            existing_metadata = {}
    except json.JSONDecodeError:
        existing_metadata = {}

    merged = dict(existing_metadata)

    if allow_metadata:
        for key, value in incoming_metadata.items():
            if key not in {"description", "is_active"}:
                merged[key] = value

    if allow_description and "description" in incoming_metadata:
        merged["description"] = incoming_metadata["description"]
    if allow_is_active and "is_active" in incoming_metadata:
        merged["is_active"] = incoming_metadata["is_active"]

    return merged


def _assert_acyclic(parent_refs: dict[str, str]) -> None:
    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(node: str) -> None:
        if node in in_stack:
            raise CoaImportError("account parent graph must be acyclic")
        if node in visited:
            return
        visited.add(node)
        in_stack.add(node)
        parent = parent_refs.get(node)
        if parent:
            dfs(parent)
        in_stack.remove(node)

    for node in parent_refs:
        dfs(node)
