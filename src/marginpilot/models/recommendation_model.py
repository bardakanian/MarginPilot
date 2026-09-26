"""Deterministic management assessment for a financial scenario."""

from __future__ import annotations

from dataclasses import dataclass

from marginpilot.models.financial_model import (
    FinancialInputs,
    FinancialResults,
    percentage_change,
)


@dataclass(frozen=True, slots=True)
class ManagementAssessment:
    """Management-facing interpretation and presentation status."""

    summary: str
    status: str
    tone: str
    assumptions_note: str


def generate_management_assessment(
    current_inputs: FinancialInputs,
    proposed_inputs: FinancialInputs,
    current: FinancialResults,
    proposed: FinancialResults,
) -> ManagementAssessment:
    """Build a concise assessment using only calculated scenario values."""

    profit_change = proposed.operating_profit - current.operating_profit
    tolerance = max(1.0, abs(current.operating_profit) * 0.0005)
    profit_pct = percentage_change(current.operating_profit, proposed.operating_profit)

    if profit_change > tolerance:
        outcome = (
            "The proposed scenario increases estimated operating profit by "
            f"{_currency(abs(profit_change))}"
        )
        if profit_pct is not None:
            outcome += f", or {abs(profit_pct):.1f}%"
        outcome += "."
    elif profit_change < -tolerance:
        outcome = (
            "The proposed scenario decreases estimated operating profit by "
            f"{_currency(abs(profit_change))}"
        )
        if profit_pct is not None:
            outcome += f", or {abs(profit_pct):.1f}%"
        outcome += "."
    else:
        outcome = (
            "The proposed scenario keeps estimated operating profit approximately "
            f"unchanged at {_currency(proposed.operating_profit)}."
        )

    if current.operating_profit == 0 and abs(profit_change) > tolerance:
        outcome += (
            " A percentage comparison is unavailable because current operating "
            "profit is zero."
        )

    comparison = _results_comparison(current, proposed)
    status, tone = _status_for(profit_change, tolerance, proposed.operating_profit)
    assumptions = _assumption_sentence(current_inputs, proposed_inputs)
    connector = "but" if tone == "positive" else "The result also"
    if tone == "positive":
        conclusion = (
            f"The strategy appears {status.lower()}, {connector} the result assumes "
            f"{assumptions}."
        )
    else:
        conclusion = (
            f"The strategy appears {status.lower()}. {connector} assumes {assumptions}."
        )

    assumptions_note = (
        f"Proposed assumptions: {proposed_inputs.units_sold:,.0f} units • "
        f"{_currency(proposed_inputs.price_per_unit, decimals=2)} per unit • "
        f"{_currency(proposed_inputs.marketing_spend)} marketing. "
        "Scenario estimates are not guaranteed forecasts."
    )
    return ManagementAssessment(
        summary=f"{outcome} {comparison} {conclusion}",
        status=status,
        tone=tone,
        assumptions_note=assumptions_note,
    )


def _results_comparison(
    current: FinancialResults, proposed: FinancialResults
) -> str:
    margin = _margin_clause(current.profit_margin, proposed.profit_margin)
    break_even = _break_even_clause(
        current.break_even_units, proposed.break_even_units
    )
    if current.profit_margin is not None and proposed.profit_margin is not None:
        if current.break_even_units is not None and proposed.break_even_units is not None:
            return f"{margin}, while {break_even}."
        return f"{margin}. {break_even}."
    return f"{margin}. {break_even}."


def _margin_clause(current: float | None, proposed: float | None) -> str:
    if current is None or proposed is None:
        return "Profit margin is unavailable because revenue is zero in one or both scenarios"
    if proposed > current + 0.05:
        verb = "rises"
    elif proposed < current - 0.05:
        verb = "falls"
    else:
        return f"Profit margin remains approximately unchanged at {proposed:.1f}%"
    return f"Profit margin {verb} from {current:.1f}% to {proposed:.1f}%"


def _break_even_clause(current: float | None, proposed: float | None) -> str:
    if current is None or proposed is None:
        return (
            "Break-even volume is unavailable because contribution margin is zero "
            "or negative in one or both scenarios"
        )
    if proposed < current - 0.5:
        verb = "break-even volume falls"
    elif proposed > current + 0.5:
        verb = "break-even volume rises"
    else:
        return f"break-even volume remains approximately unchanged at {proposed:,.0f} units"
    return f"{verb} from {current:,.0f} to {proposed:,.0f} units"


def _status_for(
    profit_change: float, tolerance: float, proposed_profit: float
) -> tuple[str, str]:
    if profit_change > tolerance and proposed_profit > 0:
        return "Financially Favorable", "positive"
    if profit_change < -tolerance or proposed_profit < 0:
        return "Financially Unfavorable", "negative"
    return "Neutral or Inconclusive", "neutral"


def _assumption_sentence(
    current: FinancialInputs, proposed: FinancialInputs
) -> str:
    price_tolerance = 0.005
    if proposed.price_per_unit > current.price_per_unit + price_tolerance:
        price_phrase = "at the higher price"
    elif proposed.price_per_unit < current.price_per_unit - price_tolerance:
        price_phrase = "at the lower price"
    else:
        price_phrase = f"at a selling price of {_currency(proposed.price_per_unit, decimals=2)}"

    if proposed.marketing_spend > current.marketing_spend + 0.5:
        marketing_phrase = (
            "while increasing marketing investment to "
            f"{_currency(proposed.marketing_spend)}"
        )
    elif proposed.marketing_spend < current.marketing_spend - 0.5:
        marketing_phrase = (
            "while reducing marketing investment to "
            f"{_currency(proposed.marketing_spend)}"
        )
    else:
        marketing_phrase = (
            "with marketing investment of " f"{_currency(proposed.marketing_spend)}"
        )
    return (
        f"the business can sell {proposed.units_sold:,.0f} units {price_phrase} "
        f"{marketing_phrase}"
    )


def _currency(value: float, *, decimals: int = 0) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.{decimals}f}"
