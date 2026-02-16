from __future__ import annotations

import random
from decimal import Decimal


def build_multi_entity_posture_payload(
    *,
    entity_count: int = 25,
    transfer_pairs: int = 12,
    seed: int = 8302,
    correlation_id: str = "corr-multi-entity",
) -> dict:
    if entity_count < 1:
        raise ValueError("entity_count must be >= 1")
    if transfer_pairs < 0:
        raise ValueError("transfer_pairs must be >= 0")

    rng = random.Random(seed)
    entity_ids = [f"entity-{index:03d}" for index in range(1, entity_count + 1)]
    entities = []

    for index, entity_id in enumerate(entity_ids, start=1):
        entities.append(
            {
                "entity_id": entity_id,
                "liquidity": f"{Decimal(10_000 + (index * 187) + rng.randint(0, 300)):.4f}",
                "fixed_burn": f"{Decimal(2_000 + (index * 21) + rng.randint(0, 50)):.4f}",
                "variable_burn": f"{Decimal(700 + (index * 9) + rng.randint(0, 25)):.4f}",
                "minimum_reserve": f"{Decimal(5_000 + (index * 61) + rng.randint(0, 90)):.4f}",
                "volatility_buffer": f"{Decimal(400 + (index * 5) + rng.randint(0, 30)):.4f}",
            }
        )

    legs: list[dict[str, str]] = []
    max_pairs = min(transfer_pairs, entity_count // 2)
    for pair_index in range(max_pairs):
        left = entity_ids[pair_index]
        right = entity_ids[-(pair_index + 1)]
        amount = Decimal(250 + (pair_index * 17))
        transfer_id = f"xfer-{pair_index + 1:03d}"
        legs.append(
            {
                "transfer_id": transfer_id,
                "entity_id": left,
                "counterparty_entity_id": right,
                "direction": "out",
                "amount": f"{amount:.4f}",
            }
        )
        legs.append(
            {
                "transfer_id": transfer_id,
                "entity_id": right,
                "counterparty_entity_id": left,
                "direction": "in",
                "amount": f"{amount:.4f}",
            }
        )

    return {
        "entity_ids": list(reversed(entity_ids)),
        "entities": list(reversed(entities)),
        "inter_entity_transfers": list(reversed(legs)),
        "correlation_id": correlation_id,
    }
