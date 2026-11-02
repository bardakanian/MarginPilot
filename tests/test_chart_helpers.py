"""Tests for chart axis rounding and currency labels."""

import pytest

from marginpilot.models.financial_model import ScenarioChanges
from marginpilot.widgets.chart_panel import (
    currency_scale,
    nice_ticks,
    sensitivity_note,
    tick_decimals,
)


@pytest.mark.parametrize(
    ("low", "high", "expected"),
    [
        (0.0, 3.6, (0.0, 4.0, 1.0)),
        (-1.1, 2.1, (-2.0, 3.0, 1.0)),
        (350.0, 548.0, (350.0, 550.0, 50.0)),
        (0.0, 0.0, (0.0, 1.0, 0.2)),
    ],
)
def test_nice_ticks_round_outward_to_readable_steps(
    low: float, high: float, expected: tuple[float, float, float]
) -> None:
    assert nice_ticks(low, high) == pytest.approx(expected)


def test_nice_ticks_always_cover_the_range() -> None:
    for low, high in [(-7.3, 13.9), (0.12, 0.97), (1_234.0, 98_765.0)]:
        start, stop, step = nice_ticks(low, high)
        assert start <= low and stop >= high
        assert 3 <= round((stop - start) / step) <= 10


def test_tick_decimals() -> None:
    assert tick_decimals(50) == 0
    assert tick_decimals(0.5) == 1
    assert tick_decimals(0.25) == 2


def test_negative_currency_labels_put_the_sign_first() -> None:
    scale = currency_scale([2_100_000.0, -400_000.0])
    assert scale.suffix == "M"
    assert scale.label(-0.4, 1) == "-$0.4M"
    assert scale.label(-0.0000001, 1) == "$0.0M"
    assert currency_scale([950.0]).label(950, 0) == "$950"


def test_sensitivity_note_explains_elasticity_setting() -> None:
    assert "elasticity is off" in sensitivity_note(ScenarioChanges(), 20, 1_000)
    note = sensitivity_note(ScenarioChanges(price_elasticity=-2), 2, 515_861)
    assert "+2.0%" in note and "$515,861" in note
