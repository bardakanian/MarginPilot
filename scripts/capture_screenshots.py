"""Capture deterministic screenshots of the real PySide6 application."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QSize, QTimer  # noqa: E402
from PySide6.QtGui import QImageReader  # noqa: E402
from PySide6.QtPdf import QPdfDocument  # noqa: E402

from marginpilot.app import create_application  # noqa: E402
from marginpilot.main_window import MainWindow  # noqa: E402
from marginpilot.models.risk_model import RiskConfig  # noqa: E402
from marginpilot.theme_manager import DARK, LIGHT  # noqa: E402
from marginpilot.widgets.glossary_dialog import BusinessGlossaryDialog  # noqa: E402


def main() -> int:
    app = create_application(["capture_screenshots"])
    app.theme_manager.apply_theme(LIGHT, persist=False)
    output = ROOT / "assets" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    window = MainWindow()
    window.resize(1440, 900)
    window.load_example()
    window.input_panel.scenario_controls["price"].set_value(4.0)
    window.input_panel.scenario_controls["volume"].set_value(6.0)
    window.input_panel.scenario_controls["variable_cost"].set_value(-2.0)
    window.input_panel.scenario_controls["fixed_cost"].set_value(0.0)
    window.input_panel.scenario_controls["marketing"].set_value(20.0)
    window.input_panel.elasticity.setValue(-1.8)
    window.update_dashboard()
    window.show()

    def capture(widget, filename: str, minimum_size: tuple[int, int]) -> None:
        app.processEvents()
        path = output / filename
        if not widget.grab().save(str(path), "PNG"):
            raise RuntimeError(f"Could not save screenshot: {path}")
        reader = QImageReader(str(path))
        size = reader.size()
        if (
            not reader.canRead()
            or size.width() < minimum_size[0]
            or size.height() < minimum_size[1]
            or path.stat().st_size < 20_000
        ):
            raise RuntimeError(f"Screenshot validation failed: {path}")

    def dashboard_light() -> None:
        window.workspace_tabs.setCurrentIndex(0)
        window.input_panel.mode_tabs.setCurrentIndex(0)
        QTimer.singleShot(300, capture_dashboard_light)

    def capture_dashboard_light() -> None:
        capture(window, "dashboard-light.png", (1400, 850))
        app.theme_manager.apply_theme(DARK, persist=False)
        QTimer.singleShot(350, capture_dashboard_dark)

    def capture_dashboard_dark() -> None:
        capture(window, "dashboard-dark.png", (1400, 850))
        glossary = BusinessGlossaryDialog(window)
        glossary.setModal(False)
        glossary.resize(1440, 900)
        glossary.show()
        window._capture_glossary = glossary
        QTimer.singleShot(300, capture_glossary_dark)

    def capture_glossary_dark() -> None:
        glossary = window._capture_glossary
        capture(glossary, "business-glossary-dark.png", (1400, 850))
        glossary.close()
        glossary.deleteLater()
        del window._capture_glossary
        app.theme_manager.apply_theme(LIGHT, persist=False)
        window.workspace_tabs.setCurrentIndex(0)
        window.input_panel.mode_tabs.setCurrentIndex(1)
        QTimer.singleShot(300, capture_csv)

    def capture_csv() -> None:
        capture(window, "csv_import.png", (1400, 850))
        app.theme_manager.apply_theme(DARK, persist=False)
        window.workspace_tabs.setCurrentIndex(1)
        window.risk_panel.volume_uncertainty.setValue(20.0)
        window.risk_panel.cost_uncertainty.setValue(12.0)
        window.run_simulation(RiskConfig(20.0, 12.0, 10_000, seed=42))
        QTimer.singleShot(450, capture_risk)

    def capture_risk() -> None:
        capture(window, "risk-analysis.png", (1400, 850))
        app.theme_manager.apply_theme(LIGHT, persist=False)
        capture_export_summary()
        window.close()
        app.quit()

    def capture_export_summary() -> None:
        """Export the real PDF and save its first page as an image."""

        with tempfile.TemporaryDirectory() as folder:
            pdf_path = Path(folder) / "summary.pdf"
            if not window.export_pdf(pdf_path):
                raise RuntimeError("The executive summary could not be exported.")
            document = QPdfDocument()
            document.load(str(pdf_path))
            if document.pageCount() != 1:
                raise RuntimeError("The executive summary should fit on one page.")
            page = document.render(0, QSize(1240, 1754))
            document.close()
        path = output / "export-summary.png"
        if not page.save(str(path), "PNG") or path.stat().st_size < 20_000:
            raise RuntimeError(f"Screenshot validation failed: {path}")

    QTimer.singleShot(500, dashboard_light)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
