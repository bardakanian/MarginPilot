"""Tests for centralized, persistent theme selection."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from marginpilot.theme_manager import DARK, LIGHT, ThemeManager


def test_theme_selection_applies_and_persists(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    settings_path = tmp_path / "marginpilot-theme.ini"
    first_settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    first = ThemeManager(app, first_settings)
    first.apply_theme(DARK)

    assert first.theme == DARK
    assert first.chart_theme.text == "#F3F4F6"
    assert "#111827" in app.styleSheet()

    second_settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    second = ThemeManager(app, second_settings)
    assert second.theme == DARK

    second.apply_theme(LIGHT)
    assert second.theme == LIGHT
    assert "#F4F7FB" in app.styleSheet()
