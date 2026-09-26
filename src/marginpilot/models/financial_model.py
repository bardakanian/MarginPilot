"""Pure financial calculations for the MarginPilot application."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class FinancialInputs:
    """Operating inputs for one financial scenario."""

    units_sold: float
    price_per_unit: float
    variable_cost_per_unit: float
    fixed_costs: float
    marketing_spend: float

    def __post_init__(self) -> None:
        values = (
            self.units_sold,
            self.price_per_unit,
            self.variable_cost_per_unit,
            self.fixed_costs,
            self.marketing_spend,
        )
        if not all(isfinite(value) for value in values):
            raise ValueError("Financial inputs must be finite numbers.")
        if any(value < 0 for value in values):
            raise ValueError("Financial inputs cannot be negative.")


@dataclass(frozen=True, slots=True)
class ScenarioChanges:
    """Percentage changes applied to a baseline scenario."""

    price: float = 0.0
    volume: float = 0.0
    variable_cost: float = 0.0
    fixed_cost: float = 0.0
    marketing: float = 0.0


@dataclass(frozen=True, slots=True)
class FinancialResults:
    """Calculated results for one operating scenario."""

    revenue: float
    variable_costs: float
    total_costs: float
    operating_profit: float
    profit_margin: float | None
    contribution_margin_per_unit: float
    break_even_units: float | None


def apply_changes(
    baseline: FinancialInputs, changes: ScenarioChanges
) -> FinancialInputs:
    """Return operating inputs after applying percentage changes."""

    return FinancialInputs(
        units_sold=baseline.units_sold * (1.0 + changes.volume / 100.0),
        price_per_unit=baseline.price_per_unit * (1.0 + changes.price / 100.0),
        variable_cost_per_unit=baseline.variable_cost_per_unit
        * (1.0 + changes.variable_cost / 100.0),
        fixed_costs=baseline.fixed_costs * (1.0 + changes.fixed_cost / 100.0),
        marketing_spend=baseline.marketing_spend
        * (1.0 + changes.marketing / 100.0),
    )


def calculate_financials(inputs: FinancialInputs) -> FinancialResults:
    """Calculate key financial results, safely handling undefined ratios."""

    revenue = inputs.units_sold * inputs.price_per_unit
    variable_costs = inputs.units_sold * inputs.variable_cost_per_unit
    total_costs = variable_costs + inputs.fixed_costs + inputs.marketing_spend
    operating_profit = revenue - total_costs
    profit_margin = (operating_profit / revenue * 100.0) if revenue > 0 else None
    contribution_margin = inputs.price_per_unit - inputs.variable_cost_per_unit
    break_even_units = (
        (inputs.fixed_costs + inputs.marketing_spend) / contribution_margin
        if contribution_margin > 0
        else None
    )
    return FinancialResults(
        revenue=revenue,
        variable_costs=variable_costs,
        total_costs=total_costs,
        operating_profit=operating_profit,
        profit_margin=profit_margin,
        contribution_margin_per_unit=contribution_margin,
        break_even_units=break_even_units,
    )


def percentage_change(current: float | None, proposed: float | None) -> float | None:
    """Return percentage change, or None when it is not mathematically meaningful."""

    if current is None or proposed is None or current == 0:
        return None
    return (proposed - current) / abs(current) * 100.0
