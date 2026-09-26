"""Tests for deterministic financial calculations."""

import pytest

from marginpilot.models.financial_model import (
    FinancialInputs,
    ScenarioChanges,
    apply_changes,
    calculate_financials,
    percentage_change,
)


def test_normal_profitable_scenario() -> None:
    results = calculate_financials(FinancialInputs(1_000, 50, 20, 10_000, 5_000))
    assert results.revenue == 50_000
    assert results.variable_costs == 20_000
    assert results.total_costs == 35_000
    assert results.operating_profit == 15_000
    assert results.profit_margin == pytest.approx(30.0)
    assert results.contribution_margin_per_unit == 30


def test_loss_making_scenario() -> None:
    results = calculate_financials(FinancialInputs(100, 10, 8, 2_000, 500))
    assert results.operating_profit == -2_300
    assert results.profit_margin == pytest.approx(-230.0)


def test_zero_revenue_and_zero_units_are_safe() -> None:
    results = calculate_financials(FinancialInputs(0, 50, 20, 1_000, 200))
    assert results.revenue == 0
    assert results.profit_margin is None
    assert results.operating_profit == -1_200


@pytest.mark.parametrize(
    ("price", "variable_cost"),
    [(10, 10), (8, 10)],
)
def test_zero_or_negative_contribution_margin_has_no_break_even(
    price: float, variable_cost: float
) -> None:
    results = calculate_financials(
        FinancialInputs(100, price, variable_cost, 1_000, 200)
    )
    assert results.break_even_units is None


def test_break_even_calculation() -> None:
    results = calculate_financials(FinancialInputs(500, 40, 25, 6_000, 1_500))
    assert results.break_even_units == pytest.approx(500.0)


def test_scenario_percentage_changes() -> None:
    baseline = FinancialInputs(1_000, 100, 50, 20_000, 10_000)
    changed = apply_changes(
        baseline,
        ScenarioChanges(
            price=10, volume=-20, variable_cost=5, fixed_cost=-10, marketing=50
        ),
    )
    assert changed.units_sold == pytest.approx(800)
    assert changed.price_per_unit == pytest.approx(110)
    assert changed.variable_cost_per_unit == pytest.approx(52.5)
    assert changed.fixed_costs == pytest.approx(18_000)
    assert changed.marketing_spend == pytest.approx(15_000)


def test_percentage_change_and_zero_denominator() -> None:
    assert percentage_change(100, 112.5) == pytest.approx(12.5)
    assert percentage_change(-100, -80) == pytest.approx(20.0)
    assert percentage_change(0, 50) is None
    assert percentage_change(None, 50) is None


def test_negative_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        FinancialInputs(-1, 10, 5, 100, 20)


def test_portfolio_demonstration_scenario_results() -> None:
    baseline = FinancialInputs(10_000, 50, 28, 120_000, 40_000)
    proposed_inputs = apply_changes(
        baseline,
        ScenarioChanges(
            price=6, volume=-3, variable_cost=2, fixed_cost=0, marketing=25
        ),
    )
    current = calculate_financials(baseline)
    proposed = calculate_financials(proposed_inputs)

    assert current.revenue == 500_000
    assert current.total_costs == 440_000
    assert current.operating_profit == 60_000
    assert current.profit_margin == pytest.approx(12.0)
    assert current.break_even_units == pytest.approx(7_272.727)

    assert proposed_inputs.units_sold == pytest.approx(9_700)
    assert proposed_inputs.price_per_unit == pytest.approx(53.0)
    assert proposed_inputs.variable_cost_per_unit == pytest.approx(28.56)
    assert proposed_inputs.fixed_costs == 120_000
    assert proposed_inputs.marketing_spend == 50_000
    assert proposed.revenue == pytest.approx(514_100)
    assert proposed.total_costs == pytest.approx(447_032)
    assert proposed.operating_profit == pytest.approx(67_068)
    assert proposed.profit_margin == pytest.approx(13.04571)
    assert proposed.break_even_units == pytest.approx(6_955.81)
    assert percentage_change(current.operating_profit, proposed.operating_profit) == pytest.approx(11.78)
