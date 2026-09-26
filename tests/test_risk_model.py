"""Tests for the Monte Carlo risk model."""

import numpy as np
import pytest

from marginpilot.models.financial_model import FinancialInputs
from marginpilot.models.risk_model import RiskConfig, run_profit_simulation


def test_risk_simulation_is_reproducible() -> None:
    current = FinancialInputs(5_000, 50, 25, 60_000, 20_000)
    proposed = FinancialInputs(5_250, 52, 24, 60_000, 24_000)
    config = RiskConfig(10, 5, 2_000, seed=42)
    first = run_profit_simulation(current, proposed, config)
    second = run_profit_simulation(current, proposed, config)
    np.testing.assert_array_equal(first.profits, second.profits)
    assert first.median == second.median
    assert first.probability_beats_current == second.probability_beats_current


def test_zero_uncertainty_matches_deterministic_profit() -> None:
    current = FinancialInputs(100, 20, 10, 200, 100)
    proposed = FinancialInputs(120, 22, 10, 200, 100)
    results = run_profit_simulation(
        current, proposed, RiskConfig(0, 0, 100, seed=7)
    )
    assert np.all(results.profits == 1_140)
    assert results.median == 1_140
    assert results.probability_beats_current == 100.0
    assert results.probability_of_loss == 0.0


def test_loss_probability_for_structural_loss() -> None:
    inputs = FinancialInputs(100, 5, 8, 1_000, 500)
    results = run_profit_simulation(inputs, inputs, RiskConfig(0, 0, 500))
    assert results.probability_of_loss == 100.0
    assert results.probability_beats_current == 0.0


def test_invalid_simulation_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="between 100 and 100,000"):
        RiskConfig(simulations=10)
