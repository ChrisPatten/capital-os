from __future__ import annotations

from capital_os.domain.simulation.engine import SimulationInputs, compute_simulation_projection_with_hash


def simulate_spend(payload: dict) -> dict:
    inputs = SimulationInputs.model_validate(payload)
    return compute_simulation_projection_with_hash(inputs)
