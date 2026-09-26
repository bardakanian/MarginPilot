"""Tests for the deterministic management assessment."""

import pytest

from marginpilot.models.financial_model import (
    FinancialInputs,
    ScenarioChanges,
    apply_changes,
    calculate_financials,
)
from marginpilot.models.recommendation_model import generate_management_assessment


DEMO_BASELINE = FinancialInputs(10_000, 50, 28, 120_000, 40_000)
DEMO_CHANGES = ScenarioChanges(
    price=6, volume=-3, variable_cost=2, fixed_cost=0, marketing=25
)


def assess(
    current_inputs: FinancialInputs, proposed_inputs: FinancialInputs
):
    return generate_management_assessment(
        current_inputs,
        proposed_inputs,
        calculate_financials(current_inputs),
        calculate_financials(proposed_inputs),
    )


def test_profitable_demonstration_assessment_matches_management_copy() -> None:
    proposed = apply_changes(DEMO_BASELINE, DEMO_CHANGES)
    assessment = assess(DEMO_BASELINE, proposed)
    assert assessment.summary == (
        "The proposed scenario increases estimated operating profit by $7,068, or "
        "11.8%. Profit margin rises from 12.0% to 13.0%, while break-even volume "
        "falls from 7,273 to 6,956 units. The strategy appears financially favorable, "
        "but the result assumes the business can sell 9,700 units at the higher price "
        "while increasing marketing investment to $50,000."
    )
    assert assessment.status == "Financially Favorable"
    assert assessment.tone == "positive"
    assert "$53.00 per unit" in assessment.assumptions_note


def test_assessment_when_operating_profit_decreases() -> None:
    proposed = apply_changes(
        DEMO_BASELINE, ScenarioChanges(price=-5, volume=-10, marketing=25)
    )
    assessment = assess(DEMO_BASELINE, proposed)
    assert "decreases estimated operating profit" in assessment.summary
    assert "at the lower price" in assessment.summary
    assert assessment.status == "Financially Unfavorable"


def test_zero_current_profit_does_not_divide_by_zero() -> None:
    current = FinancialInputs(1_000, 50, 30, 15_000, 5_000)
    proposed = FinancialInputs(1_000, 55, 30, 15_000, 5_000)
    assessment = assess(current, proposed)
    assert "increases estimated operating profit by $5,000" in assessment.summary
    assert "percentage comparison is unavailable" in assessment.summary
    assert "or inf%" not in assessment.summary


def test_loss_making_proposal_is_described_as_unfavorable() -> None:
    current = FinancialInputs(100, 10, 8, 2_000, 500)
    proposed = FinancialInputs(120, 11, 8, 2_000, 500)
    assessment = assess(current, proposed)
    assert calculate_financials(proposed).operating_profit < 0
    assert "increases estimated operating profit" in assessment.summary
    assert assessment.status == "Financially Unfavorable"


def test_zero_revenue_produces_safe_margin_language() -> None:
    current = FinancialInputs(0, 50, 20, 1_000, 200)
    proposed = FinancialInputs(0, 55, 20, 1_000, 200)
    assessment = assess(current, proposed)
    assert "Profit margin is unavailable because revenue is zero" in assessment.summary
    assert "approximately unchanged" in assessment.summary


@pytest.mark.parametrize("variable_cost", [50, 60])
def test_nonpositive_contribution_margin_has_unavailable_break_even(
    variable_cost: float,
) -> None:
    current = FinancialInputs(100, 50, variable_cost, 1_000, 200)
    proposed = FinancialInputs(100, 50, variable_cost, 1_100, 250)
    assessment = assess(current, proposed)
    assert "Break-even volume is unavailable" in assessment.summary
    assert "contribution margin is zero or negative" in assessment.summary


def test_assessment_formats_currency_percentages_and_units_consistently() -> None:
    assessment = assess(DEMO_BASELINE, apply_changes(DEMO_BASELINE, DEMO_CHANGES))
    assert "$7,068" in assessment.summary
    assert "11.8%" in assessment.summary
    assert "12.0%" in assessment.summary
    assert "9,700 units" in assessment.summary
    assert "$50,000" in assessment.summary
    assert "$53.00 per unit" in assessment.assumptions_note
