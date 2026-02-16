from __future__ import annotations

from decimal import Decimal

from capital_os.domain.ledger.invariants import normalize_amount
from capital_os.domain.posture.engine import PostureComputationInputs, compute_posture_metrics


def compute_consolidated_posture(payload: dict) -> dict:
    selected_entity_ids = sorted(payload["entity_ids"])
    entity_inputs = {item["entity_id"]: item for item in payload["entities"]}

    transfer_net_by_entity: dict[str, Decimal] = {
        entity_id: Decimal("0.0000") for entity_id in selected_entity_ids
    }
    transfer_pairs: list[dict[str, str]] = []

    transfer_groups: dict[str, list[dict]] = {}
    for leg in payload.get("inter_entity_transfers", []):
        transfer_groups.setdefault(leg["transfer_id"], []).append(leg)

    for transfer_id in sorted(transfer_groups):
        legs = transfer_groups[transfer_id]
        for leg in legs:
            leg_amount = normalize_amount(leg["amount"])
            if leg["direction"] == "in":
                transfer_net_by_entity[leg["entity_id"]] = normalize_amount(
                    transfer_net_by_entity[leg["entity_id"]] + leg_amount
                )
            else:
                transfer_net_by_entity[leg["entity_id"]] = normalize_amount(
                    transfer_net_by_entity[leg["entity_id"]] - leg_amount
                )

        involved_entities = sorted({legs[0]["entity_id"], legs[0]["counterparty_entity_id"]})
        transfer_amount = normalize_amount(legs[0]["amount"])
        transfer_pairs.append(
            {
                "transfer_id": transfer_id,
                "entity_a_id": involved_entities[0],
                "entity_b_id": involved_entities[1],
                "amount": f"{transfer_amount:.4f}",
            }
        )

    entities: list[dict] = []
    consolidated_liquidity = Decimal("0.0000")
    consolidated_fixed_burn = Decimal("0.0000")
    consolidated_variable_burn = Decimal("0.0000")
    consolidated_minimum_reserve = Decimal("0.0000")
    consolidated_volatility_buffer = Decimal("0.0000")

    for entity_id in selected_entity_ids:
        item = entity_inputs[entity_id]
        liquidity = normalize_amount(item["liquidity"])
        fixed_burn = normalize_amount(item["fixed_burn"])
        variable_burn = normalize_amount(item["variable_burn"])
        minimum_reserve = normalize_amount(item["minimum_reserve"])
        volatility_buffer = normalize_amount(item["volatility_buffer"])
        transfer_net = normalize_amount(transfer_net_by_entity.get(entity_id, Decimal("0.0000")))
        transfer_neutral_liquidity = normalize_amount(liquidity - transfer_net)

        metrics = compute_posture_metrics(
            PostureComputationInputs(
                liquidity=transfer_neutral_liquidity,
                fixed_burn=fixed_burn,
                variable_burn=variable_burn,
                minimum_reserve=minimum_reserve,
                volatility_buffer=volatility_buffer,
            )
        )

        entities.append(
            {
                "entity_id": entity_id,
                "liquidity": f"{liquidity:.4f}",
                "transfer_net": f"{transfer_net:.4f}",
                "transfer_neutral_liquidity": f"{metrics.liquidity:.4f}",
                "fixed_burn": f"{metrics.fixed_burn:.4f}",
                "variable_burn": f"{metrics.variable_burn:.4f}",
                "minimum_reserve": f"{minimum_reserve:.4f}",
                "volatility_buffer": f"{metrics.volatility_buffer:.4f}",
                "reserve_target": f"{metrics.reserve_target:.4f}",
                "liquidity_surplus": f"{metrics.liquidity_surplus:.4f}",
                "reserve_ratio": f"{metrics.reserve_ratio:.4f}",
                "risk_band": metrics.risk_band,
            }
        )

        consolidated_liquidity = normalize_amount(consolidated_liquidity + metrics.liquidity)
        consolidated_fixed_burn = normalize_amount(consolidated_fixed_burn + metrics.fixed_burn)
        consolidated_variable_burn = normalize_amount(consolidated_variable_burn + metrics.variable_burn)
        consolidated_minimum_reserve = normalize_amount(
            consolidated_minimum_reserve + minimum_reserve
        )
        consolidated_volatility_buffer = normalize_amount(
            consolidated_volatility_buffer + metrics.volatility_buffer
        )

    consolidated = compute_posture_metrics(
        PostureComputationInputs(
            liquidity=consolidated_liquidity,
            fixed_burn=consolidated_fixed_burn,
            variable_burn=consolidated_variable_burn,
            minimum_reserve=consolidated_minimum_reserve,
            volatility_buffer=consolidated_volatility_buffer,
        )
    )

    return {
        "entity_ids": selected_entity_ids,
        "entities": entities,
        "transfer_pairs": transfer_pairs,
        "fixed_burn": f"{consolidated.fixed_burn:.4f}",
        "variable_burn": f"{consolidated.variable_burn:.4f}",
        "volatility_buffer": f"{consolidated.volatility_buffer:.4f}",
        "reserve_target": f"{consolidated.reserve_target:.4f}",
        "liquidity": f"{consolidated.liquidity:.4f}",
        "liquidity_surplus": f"{consolidated.liquidity_surplus:.4f}",
        "reserve_ratio": f"{consolidated.reserve_ratio:.4f}",
        "risk_band": consolidated.risk_band,
    }
