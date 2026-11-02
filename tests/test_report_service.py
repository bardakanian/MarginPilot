"""Tests for executive-summary CSV and PDF exports."""

import csv
from datetime import datetime
from pathlib import Path

import pytest

from marginpilot.models.financial_model import (
    FinancialInputs,
    ScenarioChanges,
    apply_changes,
    calculate_financials,
)
from marginpilot.models.recommendation_model import generate_management_assessment
from marginpilot.services.report_service import (
    ScenarioSnapshot,
    build_report_html,
    format_change,
    report_rows,
    write_pdf_report,
    write_scenario_csv,
)


def make_snapshot(
    baseline: FinancialInputs | None = None,
    changes: ScenarioChanges | None = None,
    source_name: str | None = "example_sales.csv",
) -> ScenarioSnapshot:
    baseline = baseline or FinancialInputs(10_000, 50, 28, 120_000, 40_000)
    changes = changes or ScenarioChanges(price=6, volume=-3, marketing=25, price_elasticity=-1)
    proposed_inputs = apply_changes(baseline, changes)
    current = calculate_financials(baseline)
    proposed = calculate_financials(proposed_inputs)
    return ScenarioSnapshot(
        baseline=baseline,
        proposed_inputs=proposed_inputs,
        changes=changes,
        current=current,
        proposed=proposed,
        assessment=generate_management_assessment(
            baseline, proposed_inputs, current, proposed, price_elasticity=-1
        ),
        source_name=source_name,
        generated_at=datetime(2026, 11, 1, 9, 30),
    )


def test_rows_cover_results_then_assumptions() -> None:
    rows = report_rows(make_snapshot())
    assert [row.section for row in rows].count("Results") == 6
    assert rows[0].item == "Revenue"
    assert rows[-1].item == "Marketing spend"
    assert rows[-1].change_pct == pytest.approx(25.0)


def test_margin_changes_are_reported_in_points() -> None:
    margin = next(row for row in report_rows(make_snapshot()) if row.item == "Profit margin")
    assert margin.change_pct is None
    assert format_change(margin).endswith(" pp")


def test_undefined_values_are_reported_as_not_available() -> None:
    snapshot = make_snapshot(baseline=FinancialInputs(0, 10, 12, 1_000, 0))
    margin = next(row for row in report_rows(snapshot) if row.item == "Profit margin")
    assert margin.current is None
    assert format_change(margin) == "N/A"


def test_csv_export_round_trips_unrounded_figures(tmp_path: Path) -> None:
    snapshot = make_snapshot()
    path = write_scenario_csv(snapshot, tmp_path / "scenario.csv")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    revenue = next(row for row in rows if row["item"] == "Revenue")
    assert float(revenue["proposed"]) == pytest.approx(snapshot.proposed.revenue)
    elasticity = next(row for row in rows if row["item"] == "Price elasticity of demand")
    assert elasticity["proposed"] == "-1.0"
    status = next(row for row in rows if row["item"] == "Status")
    assert status["proposed"] == snapshot.assessment.status


def test_report_html_escapes_file_names() -> None:
    html = build_report_html(make_snapshot(source_name="<q4>&plan.csv"))
    assert "&lt;q4&gt;&amp;plan.csv" in html
    assert "<q4>" not in html
    assert "Generated 2026-11-01 09:30" in html


def test_report_html_without_charts_or_source() -> None:
    html = build_report_html(make_snapshot(source_name=None))
    assert "Manual entry" in html
    assert "<img" not in html


def test_pdf_export_writes_a_pdf(qapp, tmp_path: Path) -> None:
    path = write_pdf_report(make_snapshot(), tmp_path / "summary.pdf")
    assert path.read_bytes().startswith(b"%PDF")
