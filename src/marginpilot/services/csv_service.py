"""Validated CSV import and baseline aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from marginpilot.models.financial_model import FinancialInputs

REQUIRED_COLUMNS = (
    "period",
    "units_sold",
    "price_per_unit",
    "variable_cost_per_unit",
    "fixed_costs",
    "marketing_spend",
)
NUMERIC_COLUMNS = REQUIRED_COLUMNS[1:]


class CSVValidationError(ValueError):
    """An import error written for display directly to an end user."""


@dataclass(slots=True)
class ImportedData:
    """Original imported rows plus their weighted aggregate baseline."""

    dataframe: pd.DataFrame
    baseline: FinancialInputs
    source: Path


def load_csv(path: str | Path) -> ImportedData:
    """Load, validate, and aggregate a MarginPilot CSV file."""

    source = Path(path)
    try:
        dataframe = pd.read_csv(source)
    except FileNotFoundError as exc:
        raise CSVValidationError(f"The file was not found: {source}") from exc
    except (pd.errors.ParserError, UnicodeDecodeError, OSError) as exc:
        raise CSVValidationError(f"The CSV could not be read: {exc}") from exc

    if dataframe.empty:
        raise CSVValidationError("The CSV is empty. Add at least one data row.")

    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise CSVValidationError(
            "Missing required column(s): " + ", ".join(missing) + "."
        )

    validated = dataframe[list(REQUIRED_COLUMNS)].copy()
    missing_period = validated["period"].isna() | (
        validated["period"].astype(str).str.strip() == ""
    )
    if missing_period.any():
        raise CSVValidationError(
            f"The period value is missing in row(s): {_row_numbers(missing_period)}."
        )

    for column in NUMERIC_COLUMNS:
        converted = pd.to_numeric(validated[column], errors="coerce")
        invalid = converted.isna() | ~np.isfinite(converted)
        if invalid.any():
            raise CSVValidationError(
                f"Column '{column}' contains a missing or invalid number in row(s): "
                f"{_row_numbers(invalid)}."
            )
        negative = converted < 0
        if negative.any():
            raise CSVValidationError(
                f"Column '{column}' contains a negative value in row(s): "
                f"{_row_numbers(negative)}. Values must be zero or greater."
            )
        validated[column] = converted.astype(float)

    total_units = float(validated["units_sold"].sum())
    revenue = float((validated["units_sold"] * validated["price_per_unit"]).sum())
    variable_costs = float(
        (validated["units_sold"] * validated["variable_cost_per_unit"]).sum()
    )
    average_price = revenue / total_units if total_units > 0 else 0.0
    average_variable_cost = variable_costs / total_units if total_units > 0 else 0.0
    baseline = FinancialInputs(
        units_sold=total_units,
        price_per_unit=average_price,
        variable_cost_per_unit=average_variable_cost,
        fixed_costs=float(validated["fixed_costs"].sum()),
        marketing_spend=float(validated["marketing_spend"].sum()),
    )
    return ImportedData(dataframe=validated, baseline=baseline, source=source)


def _row_numbers(mask: pd.Series) -> str:
    """Convert a pandas mask to human-friendly CSV row numbers."""

    return ", ".join(str(index + 2) for index in mask[mask].index.tolist())
