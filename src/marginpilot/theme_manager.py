"""Centralized application theme selection and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject


LIGHT = "light"
DARK = "dark"


@dataclass(frozen=True, slots=True)
class ChartTheme:
    """Colors used by QtCharts, which does not inherit every QSS color."""

    background: str
    plot_background: str
    text: str
    secondary_text: str
    axis: str
    grid: str
    current: str
    proposed: str
    line: str
    marker: str
    marker_border: str
    histogram: str
    zero: str


CHART_THEMES = {
    LIGHT: ChartTheme(
        background="#FFFFFF",
        plot_background="#F8FAFD",
        text="#172033",
        secondary_text="#5F6B7A",
        axis="#718096",
        grid="#DCE3EC",
        current="#2563EB",
        proposed="#0F9F8F",
        line="#2563EB",
        marker="#0F9F8F",
        marker_border="#08756A",
        histogram="#2563EB",
        zero="#64748B",
    ),
    DARK: ChartTheme(
        background="#243044",
        plot_background="#1F2937",
        text="#F3F4F6",
        secondary_text="#B6C0CF",
        axis="#94A3B8",
        grid="#3D4A5E",
        current="#60A5FA",
        proposed="#34D399",
        line="#60A5FA",
        marker="#34D399",
        marker_border="#A7F3D0",
        histogram="#60A5FA",
        zero="#CBD5E1",
    ),
}


class ThemeManager(QObject):
    """Apply one application-wide theme and remember the user's choice."""

    themeChanged = Signal(str)
    SETTINGS_KEY = "appearance/theme"

    def __init__(
        self, application: QApplication, settings: QSettings | None = None
    ) -> None:
        super().__init__(application)
        self._application = application
        self._settings = settings or QSettings()
        saved = self._settings.value(self.SETTINGS_KEY, "", type=str)
        self._theme = saved if saved in (LIGHT, DARK) else self._system_theme()
        self.apply_theme(self._theme, persist=False)

    @property
    def theme(self) -> str:
        return self._theme

    @property
    def chart_theme(self) -> ChartTheme:
        return CHART_THEMES[self._theme]

    def toggle(self) -> str:
        """Switch themes, persist the selection, and return the new theme."""

        next_theme = DARK if self._theme == LIGHT else LIGHT
        self.apply_theme(next_theme, persist=True)
        return next_theme

    def apply_theme(self, theme: str, *, persist: bool = True) -> None:
        """Apply a validated theme to every Qt window immediately."""

        if theme not in (LIGHT, DARK):
            raise ValueError(f"Unknown theme: {theme}")
        qss_name = "dark_theme.qss" if theme == DARK else "light_theme.qss"
        stylesheet = files("marginpilot.resources").joinpath(qss_name).read_text(
            encoding="utf-8"
        )
        self._application.setPalette(_palette_for(theme))
        self._application.setStyleSheet(stylesheet)
        changed = theme != self._theme
        self._theme = theme
        if persist:
            self._settings.setValue(self.SETTINGS_KEY, theme)
            self._settings.sync()
        if changed or persist:
            self.themeChanged.emit(theme)

    @staticmethod
    def _system_theme() -> str:
        """Use the operating-system preference on first run when Qt exposes it."""

        try:
            if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                return DARK
        except AttributeError:
            pass
        return LIGHT


def _palette_for(theme: str) -> QPalette:
    colors = (
        {
            "window": "#111827",
            "card": "#243044",
            "alternate": "#1F2937",
            "text": "#F3F4F6",
            "muted": "#B6C0CF",
            "button": "#243044",
            "highlight": "#60A5FA",
            "highlighted": "#0B1220",
        }
        if theme == DARK
        else {
            "window": "#F4F7FB",
            "card": "#FFFFFF",
            "alternate": "#F0F4F8",
            "text": "#172033",
            "muted": "#5F6B7A",
            "button": "#FFFFFF",
            "highlight": "#2563EB",
            "highlighted": "#FFFFFF",
        }
    )
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(colors["window"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["card"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["alternate"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["button"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["card"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["highlight"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["highlighted"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(colors["muted"]))
    return palette
