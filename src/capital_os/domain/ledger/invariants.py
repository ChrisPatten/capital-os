from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN

MONEY_QUANT = Decimal("0.0001")


class InvariantError(ValueError):
    pass


def normalize_amount(value: Decimal | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_EVEN)


def ensure_balanced(postings: list[dict]) -> None:
    total = sum((normalize_amount(p["amount"]) for p in postings), Decimal("0.0000"))
    if total != Decimal("0.0000"):
        raise InvariantError("Transaction bundle must balance to zero")
