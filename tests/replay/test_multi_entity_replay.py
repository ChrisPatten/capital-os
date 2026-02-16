from __future__ import annotations

import random

import pytest

from capital_os.tools.compute_capital_posture import handle as compute_capital_posture_tool
from capital_os.tools.compute_consolidated_posture import handle as compute_consolidated_posture_tool
from tests.support.multi_entity import build_multi_entity_posture_payload


def test_multi_entity_isolated_and_consolidated_outputs_are_reproducible(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    payload = build_multi_entity_posture_payload(entity_count=25, transfer_pairs=10)

    for entity in payload["entities"][:8]:
        isolated = {
            "liquidity": entity["liquidity"],
            "fixed_burn": entity["fixed_burn"],
            "variable_burn": entity["variable_burn"],
            "minimum_reserve": entity["minimum_reserve"],
            "volatility_buffer": entity["volatility_buffer"],
            "correlation_id": f"corr-isolated-{entity['entity_id']}",
        }
        first = compute_capital_posture_tool(isolated).model_dump(mode="json")
        second = compute_capital_posture_tool(isolated).model_dump(mode="json")
        assert first == second
        assert first["output_hash"] == second["output_hash"]

    first_consolidated = compute_consolidated_posture_tool(payload).model_dump(mode="json")
    second_consolidated = compute_consolidated_posture_tool(payload).model_dump(mode="json")

    assert first_consolidated == second_consolidated
    assert first_consolidated["output_hash"] == second_consolidated["output_hash"]


def test_multi_entity_consolidated_output_is_order_stable(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    payload = build_multi_entity_posture_payload(entity_count=25, transfer_pairs=12)
    shuffled_payload = {
        "entity_ids": payload["entity_ids"][:],
        "entities": payload["entities"][:],
        "inter_entity_transfers": payload["inter_entity_transfers"][:],
        "correlation_id": payload["correlation_id"],
    }
    rng = random.Random(2026)
    rng.shuffle(shuffled_payload["entity_ids"])
    rng.shuffle(shuffled_payload["entities"])
    rng.shuffle(shuffled_payload["inter_entity_transfers"])

    first = compute_consolidated_posture_tool(payload).model_dump(mode="json")
    second = compute_consolidated_posture_tool(shuffled_payload).model_dump(mode="json")

    assert first == second
    assert first["output_hash"] == second["output_hash"]
