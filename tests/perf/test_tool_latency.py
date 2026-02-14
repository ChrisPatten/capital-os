import statistics
import time
from decimal import Decimal

import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle
from capital_os.tools.compute_capital_posture import handle as compute_capital_posture


@pytest.mark.performance
def test_record_transaction_bundle_p95_under_300ms_smoke(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        a1 = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        a2 = create_account(conn, {"code": "9500", "name": "Perf Equity", "account_type": "equity"})

    timings = []
    for i in range(25):
        start = time.perf_counter()
        record_transaction_bundle(
            {
                "source_system": "pytest",
                "external_id": f"perf-{i}",
                "date": "2026-01-01T00:00:00Z",
                "description": "perf",
                "postings": [
                    {"account_id": a1, "amount": "1.00", "currency": "USD"},
                    {"account_id": a2, "amount": "-1.00", "currency": "USD"},
                ],
                "correlation_id": f"corr-perf-{i}",
            }
        )
        timings.append((time.perf_counter() - start) * 1000)

    p95 = statistics.quantiles(timings, n=20)[-1]
    assert p95 < 300


@pytest.mark.performance
def test_compute_capital_posture_p95_under_300ms_reference_profile():
    timings = []
    payload = {
        "liquidity": "5000000.0000",
        "fixed_burn": "120000.0000",
        "variable_burn": "35000.0000",
        "minimum_reserve": "4200000.0000",
        "volatility_buffer": "250000.0000",
        "correlation_id": "corr-posture-perf",
    }

    for _ in range(50):
        start = time.perf_counter()
        response = compute_capital_posture(payload)
        timings.append((time.perf_counter() - start) * 1000)
        assert response.explanation.reserve_assumptions.reserve_target == Decimal("4450000.0000")

    p95 = statistics.quantiles(timings, n=20)[-1]
    assert p95 < 300
