"""Application bootstrap for MarginPilot."""

from __future__ import annotations

import sys

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from marginpilot.main_window import MainWindow
from marginpilot.theme_manager import ThemeManager


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and style the QApplication instance."""

    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName("MarginPilot")
    app.setApplicationDisplayName("MarginPilot — Interactive Profit Scenario Analyzer")
    app.setOrganizationName("MarginPilot Project")
    app.setStyle("Fusion")
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    if font.family().lower() in {"sans serif", "sans-serif"}:
        installed = set(QFontDatabase.families())
        for candidate in ("Arial", "Helvetica Neue", "Helvetica", "DejaVu Sans", "Noto Sans"):
            if candidate in installed:
                font.setFamily(candidate)
                break
    font.setPointSize(10)
    app.setFont(font)
    app.theme_manager = ThemeManager(app)  # type: ignore[attr-defined]
    return app


def main() -> int:
    """Run the MarginPilot desktop application."""

    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()
