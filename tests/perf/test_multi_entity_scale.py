from __future__ import annotations

import statistics
import time

import pytest

from capital_os.tools.compute_consolidated_posture import handle as compute_consolidated_posture_tool
from tests.support.multi_entity import build_multi_entity_posture_payload


@pytest.mark.performance
def test_multi_entity_scale_payload_supports_at_least_25_entities():
    payload = build_multi_entity_posture_payload(entity_count=25, transfer_pairs=12)
    assert len(payload["entity_ids"]) >= 25
    assert len(payload["entities"]) >= 25


@pytest.mark.performance
def test_compute_consolidated_posture_p95_and_degradation_within_budget(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    payload = build_multi_entity_posture_payload(entity_count=25, transfer_pairs=12)
    timings_ms: list[float] = []
    output_hashes: list[str] = []

    for _ in range(45):
        started = time.perf_counter()
        response = compute_consolidated_posture_tool(payload)
        timings_ms.append((time.perf_counter() - started) * 1000)
        output_hashes.append(response.output_hash)

    baseline_window = timings_ms[:15]
    measured_window = timings_ms[15:]
    baseline_median = statistics.median(baseline_window)
    measured_median = statistics.median(measured_window)
    measured_p95 = statistics.quantiles(measured_window, n=20)[-1]

    assert len(set(output_hashes)) == 1
    assert measured_p95 < 300
    assert measured_median <= baseline_median * 1.20
