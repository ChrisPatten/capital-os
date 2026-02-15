from __future__ import annotations

import base64
import json


def encode_cursor(payload: dict[str, str]) -> str:
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(serialized).decode("ascii")


def decode_cursor(cursor: str) -> dict[str, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive parsing path
        raise ValueError("Invalid cursor format") from exc

    if not isinstance(payload, dict):
        raise ValueError("Invalid cursor payload")
    if payload.get("v") != 1:
        raise ValueError("Unsupported cursor version")
    if not isinstance(payload.get("code"), str) or not isinstance(payload.get("account_id"), str):
        raise ValueError("Cursor missing required sort keys")
    return payload

