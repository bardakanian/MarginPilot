"""Reproducible Monte Carlo risk simulation for proposed operating profit."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from marginpilot.models.financial_model import FinancialInputs, calculate_financials


@dataclass(frozen=True, slots=True)
class RiskConfig:
    """Configuration for a risk simulation."""

    volume_uncertainty_pct: float = 10.0
    variable_cost_uncertainty_pct: float = 5.0
    simulations: int = 10_000
    seed: int = 42

    def __post_init__(self) -> None:
        if self.volume_uncertainty_pct < 0 or self.variable_cost_uncertainty_pct < 0:
            raise ValueError("Uncertainty percentages cannot be negative.")
        if not 100 <= self.simulations <= 100_000:
            raise ValueError("Simulations must be between 100 and 100,000.")


@dataclass(frozen=True, slots=True)
class RiskResults:
    """Summary metrics and raw simulated operating profits."""

    probability_beats_current: float
    probability_of_loss: float
    percentile_10: float
    median: float
    percentile_90: float
    profits: NDArray[np.float64]


def run_profit_simulation(
    current: FinancialInputs,
    proposed: FinancialInputs,
    config: RiskConfig,
) -> RiskResults:
    """Simulate profit using normally distributed volume and unit-cost risk."""

    rng = np.random.default_rng(config.seed)
    volumes = rng.normal(
        proposed.units_sold,
        proposed.units_sold * config.volume_uncertainty_pct / 100.0,
        config.simulations,
    )
    unit_costs = rng.normal(
        proposed.variable_cost_per_unit,
        proposed.variable_cost_per_unit
        * config.variable_cost_uncertainty_pct
        / 100.0,
        config.simulations,
    )
    volumes = np.clip(volumes, 0.0, None)
    unit_costs = np.clip(unit_costs, 0.0, None)
    profits = (
        volumes * proposed.price_per_unit
        - volumes * unit_costs
        - proposed.fixed_costs
        - proposed.marketing_spend
    ).astype(np.float64)
    current_profit = calculate_financials(current).operating_profit
    percentiles = np.percentile(profits, [10, 50, 90])
    return RiskResults(
        probability_beats_current=float(np.mean(profits > current_profit) * 100.0),
        probability_of_loss=float(np.mean(profits < 0.0) * 100.0),
        percentile_10=float(percentiles[0]),
        median=float(percentiles[1]),
        percentile_90=float(percentiles[2]),
        profits=profits,
    )
