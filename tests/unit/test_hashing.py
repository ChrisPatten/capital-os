from datetime import datetime, timezone
from decimal import Decimal

from capital_os.observability.hashing import canonical_json, payload_hash


def test_hash_stable_for_dict_key_order():
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert payload_hash(a) == payload_hash(b)


def test_decimal_and_datetime_normalization():
    payload = {
        "amount": Decimal("1.23000"),
        "at": datetime(2026, 1, 1, 1, 2, 3, 123456, tzinfo=timezone.utc),
    }
    encoded = canonical_json(payload)
    assert '"1.2300"' in encoded
    assert "2026-01-01T01:02:03.123456Z" in encoded
