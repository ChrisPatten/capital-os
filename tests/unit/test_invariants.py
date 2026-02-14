from decimal import Decimal

import pytest

from capital_os.domain.ledger.invariants import InvariantError, ensure_balanced, normalize_amount


def test_normalize_round_half_even():
    assert normalize_amount("1.00505") == Decimal("1.0050")
    assert normalize_amount("1.00515") == Decimal("1.0052")


def test_unbalanced_postings_rejected():
    postings = [
        {"account_id": "a", "amount": "1.0000"},
        {"account_id": "b", "amount": "-0.9999"},
    ]
    with pytest.raises(InvariantError):
        ensure_balanced(postings)
