"""End-to-end checks of the real window, run headless with pytest-qt."""

import csv
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from marginpilot.theme_manager import DARK


def test_example_loads_into_baseline(window) -> None:
    window.load_example()
    baseline = window.input_panel.baseline()
    assert baseline.units_sold == pytest.approx(61_120)
    assert window.scenario_badge.text() == "BASELINE"
    assert window.input_panel.table_model.rowCount() == 12
    assert window.input_panel.table_model.data(
        window.input_panel.table_model.index(0, 1)
    ) == "3,820"
    assert "example_sales.csv" in window.statusBar().currentMessage()


def test_slider_drives_kpis_and_assessment(window, qtbot) -> None:
    window.load_example()
    revenue_before = window.kpi_cards["revenue"].proposed_label.text()
    slider = window.input_panel.scenario_controls["price"].slider
    slider.setFocus()
    qtbot.keyClick(slider, Qt.Key.Key_PageUp)  # +1.0%
    assert window.input_panel.scenario_controls["price"].value() == pytest.approx(1.0)
    assert window.kpi_cards["revenue"].proposed_label.text() != revenue_before
    assert window.scenario_badge.text() == "ACTIVE SCENARIO"
    assert "increases estimated operating profit" in window.recommendation.summary.text()
    assert window.kpi_cards["profit_margin"].change_label.text().split("\n")[0].endswith("pp")


def test_elasticity_links_volume_to_price(window) -> None:
    window.load_example()
    controls = window.input_panel.scenario_controls
    controls["price"].set_value(10.0, emit=True)
    units_without = window.current_snapshot().proposed_inputs.units_sold
    window.input_panel.elasticity.setValue(-2.0)
    snapshot = window.current_snapshot()
    assert snapshot.proposed_inputs.units_sold < units_without
    assert "elasticity -2.0" in window.sensitivity_chart.note.text()
    assert "price elasticity -2.0" in window.recommendation.note.text()


def test_reset_restores_defaults(window) -> None:
    window.load_example()
    window.input_panel.scenario_controls["marketing"].set_value(30.0, emit=True)
    window.input_panel.elasticity.setValue(-1.5)
    window.reset_application()
    assert window.input_panel.baseline() == window.input_panel.DEFAULTS
    assert window.input_panel.changes().price_elasticity == 0
    assert window.scenario_badge.text() == "BASELINE"
    assert window.input_panel.imported_data is None


def test_invalid_csv_is_reported_not_raised(window, tmp_path: Path, monkeypatch) -> None:
    warnings: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda _parent, _title, text: warnings.append(text)
    )
    bad = tmp_path / "bad.csv"
    bad.write_text("period,units_sold\n2025-01,10\n", encoding="utf-8")
    baseline_before = window.input_panel.baseline()
    assert window.load_csv_path(bad) is False
    assert warnings and "Missing required column" in warnings[0]
    assert window.input_panel.baseline() == baseline_before


def test_simulation_fills_risk_metrics_reproducibly(window) -> None:
    window.load_example()
    window.run_simulation()
    first = [metric.value.text() for metric in window.risk_panel.metrics]
    window.run_simulation()
    assert [metric.value.text() for metric in window.risk_panel.metrics] == first
    assert all(text != "—" for text in first)


def test_theme_switch_repaints_without_losing_state(window) -> None:
    window.load_example()
    window.input_panel.scenario_controls["price"].set_value(5.0, emit=True)
    window.run_simulation()
    window.theme_manager.apply_theme(DARK, persist=False)
    assert window.theme_button.text() == "Theme: Dark"
    assert window.input_panel.scenario_controls["price"].value() == pytest.approx(5.0)
    assert window.risk_panel.metrics[0].value.text() != "—"


def test_exports_write_pdf_and_csv(window, tmp_path: Path) -> None:
    window.load_example()
    window.input_panel.scenario_controls["price"].set_value(6.0, emit=True)
    pdf = tmp_path / "summary.pdf"
    data = tmp_path / "scenario.csv"
    assert window.export_pdf(pdf)
    assert window.export_csv(data)
    assert pdf.read_bytes().startswith(b"%PDF")
    with data.open(newline="", encoding="utf-8") as handle:
        items = {row["item"]: row for row in csv.DictReader(handle)}
    assert float(items["Selling price / unit"]["proposed"]) == pytest.approx(
        window.current_snapshot().proposed_inputs.price_per_unit
    )
    assert "Exported scenario.csv" in window.statusBar().currentMessage()


def test_export_failure_is_reported(window, tmp_path: Path, monkeypatch) -> None:
    warnings: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda _parent, _title, text: warnings.append(text)
    )
    assert window.export_csv(tmp_path / "missing-folder" / "scenario.csv") is False
    assert warnings and "could not be saved" in warnings[0]
