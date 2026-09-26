"""Tests for CSV validation and weighted aggregation."""

from pathlib import Path

import pytest

from marginpilot.services.csv_service import CSVValidationError, load_csv


VALID_HEADER = (
    "period,units_sold,price_per_unit,variable_cost_per_unit,fixed_costs,marketing_spend\n"
)


def write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_csv_aggregation_uses_weighted_unit_averages(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "sales.csv",
        VALID_HEADER + "Jan,100,10,4,1000,200\nFeb,300,20,8,1200,300\n",
    )
    imported = load_csv(path)
    assert imported.baseline.units_sold == 400
    assert imported.baseline.price_per_unit == pytest.approx(17.5)
    assert imported.baseline.variable_cost_per_unit == pytest.approx(7.0)
    assert imported.baseline.fixed_costs == 2_200
    assert imported.baseline.marketing_spend == 500
    assert list(imported.dataframe["period"]) == ["Jan", "Feb"]


def test_missing_csv_columns_get_specific_error(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "missing.csv", "period,units_sold\nJan,100\n")
    with pytest.raises(CSVValidationError, match="Missing required column") as exc:
        load_csv(path)
    assert "price_per_unit" in str(exc.value)


@pytest.mark.parametrize("bad_value", ["hello", "", "NaN", "inf"])
def test_invalid_csv_values_are_rejected(tmp_path: Path, bad_value: str) -> None:
    path = write_csv(
        tmp_path / "invalid.csv",
        VALID_HEADER + f"Jan,100,{bad_value},4,1000,200\n",
    )
    with pytest.raises(CSVValidationError, match="price_per_unit"):
        load_csv(path)


def test_negative_csv_values_are_rejected(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "negative.csv",
        VALID_HEADER + "Jan,100,10,-4,1000,200\n",
    )
    with pytest.raises(CSVValidationError, match="negative value"):
        load_csv(path)


def test_zero_units_csv_aggregates_safely(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "zero.csv",
        VALID_HEADER + "Jan,0,10,4,1000,200\n",
    )
    imported = load_csv(path)
    assert imported.baseline.units_sold == 0
    assert imported.baseline.price_per_unit == 0
    assert imported.baseline.variable_cost_per_unit == 0


def test_empty_csv_is_rejected(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "empty.csv", VALID_HEADER)
    with pytest.raises(CSVValidationError, match="empty"):
        load_csv(path)
