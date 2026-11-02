"""Pure financial calculations for the MarginPilot application."""

from __future__ import annotations

from dataclasses import dataclass, replace
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


MIN_PRICE_ELASTICITY = -5.0


@dataclass(frozen=True, slots=True)
class ScenarioChanges:
    """Percentage changes applied to a baseline scenario.

    ``price_elasticity`` is the constant price elasticity of demand. At 0 (the
    default) volume ignores price; at -1.5 a 1% price rise costs about 1.5% of
    volume, on top of the independent ``volume`` change.
    """

    price: float = 0.0
    volume: float = 0.0
    variable_cost: float = 0.0
    fixed_cost: float = 0.0
    marketing: float = 0.0
    price_elasticity: float = 0.0

    def __post_init__(self) -> None:
        if not isfinite(self.price_elasticity):
            raise ValueError("Price elasticity must be a finite number.")
        if not MIN_PRICE_ELASTICITY <= self.price_elasticity <= 0:
            raise ValueError(
                f"Price elasticity must be between {MIN_PRICE_ELASTICITY:g} and 0."
            )
        if self.price <= -100:
            raise ValueError("Price cannot fall by 100% or more.")

    @property
    def is_active(self) -> bool:
        """Whether any percentage lever differs from the baseline."""

        return any(
            abs(value) > 0.0001
            for value in (
                self.price,
                self.volume,
                self.variable_cost,
                self.fixed_cost,
                self.marketing,
            )
        )


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

    price_factor = 1.0 + changes.price / 100.0
    demand_response = price_factor**changes.price_elasticity
    return FinancialInputs(
        units_sold=baseline.units_sold
        * (1.0 + changes.volume / 100.0)
        * demand_response,
        price_per_unit=baseline.price_per_unit * price_factor,
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


@dataclass(frozen=True, slots=True)
class SensitivityPoint:
    """Operating profit at one price change, all other levers held."""

    price_change: float
    operating_profit: float


def price_sensitivity(
    baseline: FinancialInputs,
    changes: ScenarioChanges,
    *,
    low: float = -20.0,
    high: float = 20.0,
    step: float = 0.5,
) -> list[SensitivityPoint]:
    """Profit across a price-change range, keeping every other lever fixed."""

    if step <= 0 or high < low:
        raise ValueError("The sensitivity range must have a positive step.")
    count = round((high - low) / step)
    points = []
    for index in range(count + 1):
        price_change = low + index * step
        varied = replace(changes, price=price_change)
        profit = calculate_financials(apply_changes(baseline, varied)).operating_profit
        points.append(SensitivityPoint(price_change, profit))
    return points


def best_price_change(points: list[SensitivityPoint]) -> SensitivityPoint:
    """Return the most profitable point; ties go to the smallest price change."""

    if not points:
        raise ValueError("At least one sensitivity point is required.")
    return max(points, key=lambda point: (point.operating_profit, -abs(point.price_change)))
