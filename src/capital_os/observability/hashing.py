from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN

MONEY_QUANT = Decimal("0.0001")


def _normalize(obj):
    if isinstance(obj, dict):
        return {k: _normalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_normalize(x) for x in obj]
    if isinstance(obj, Decimal):
        return str(obj.quantize(MONEY_QUANT, rounding=ROUND_HALF_EVEN))
    if isinstance(obj, datetime):
        dt = obj.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        # Truncate to microseconds by reconstruction.
        dt = dt.replace(microsecond=dt.microsecond)
        return dt.isoformat().replace("+00:00", "Z")
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def canonical_json(payload: dict) -> str:
    return json.dumps(_normalize(payload), separators=(",", ":"), sort_keys=True)


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
