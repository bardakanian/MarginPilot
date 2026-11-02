"""Shared fixtures; Qt runs headless so the suite works in CI."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from marginpilot.theme_manager import LIGHT, ThemeManager


@pytest.fixture
def window(qapp: QApplication, qtbot, tmp_path: Path) -> Iterator:
    """A main window whose theme choice is saved in a throwaway settings file."""

    from marginpilot.main_window import MainWindow

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager = ThemeManager(qapp, settings)
    manager.apply_theme(LIGHT, persist=False)
    qapp.theme_manager = manager  # type: ignore[attr-defined]
    main_window = MainWindow()
    qtbot.addWidget(main_window)
    yield main_window
    main_window.close()
