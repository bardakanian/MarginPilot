"""Accessible KPI comparison card."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from marginpilot.models.financial_model import percentage_change


class KpiCard(QFrame):
    """Shows current, proposed, and direction-aware KPI changes."""

    def __init__(
        self,
        title: str,
        formatter: Callable[[float | None], str],
        *,
        lower_is_better: bool = False,
    ) -> None:
        super().__init__()
        self.setObjectName("kpiCard")
        self._formatter = formatter
        self._lower_is_better = lower_is_better
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("kpiTitle")
        self.proposed_label = QLabel("—")
        self.proposed_label.setObjectName("kpiValue")
        self.current_label = QLabel("Current: —")
        self.current_label.setObjectName("kpiCurrent")
        self.change_label = QLabel("Unchanged")
        self.change_label.setObjectName("neutralChange")
        self.change_label.setWordWrap(True)
        self.change_label.setMinimumHeight(27)
        self.change_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.title_label)
        layout.addWidget(self.proposed_label)
        layout.addWidget(self.current_label)
        layout.addWidget(self.change_label)

    def update_values(self, current: float | None, proposed: float | None) -> None:
        self.proposed_label.setText(self._formatter(proposed))
        self.current_label.setText(f"Current: {self._formatter(current)}")
        if current is None or proposed is None:
            self._set_change("Not comparable", "neutralChange")
            return
        difference = proposed - current
        pct = percentage_change(current, proposed)
        if abs(difference) < 0.005:
            self._set_change("→ $0  ·  Unchanged" if self._formatter(0).startswith("$") else "→ 0  ·  Unchanged", "neutralChange")
            return
        improvement = difference < 0 if self._lower_is_better else difference > 0
        arrow = "↑" if difference > 0 else "↓"
        sign = "+" if difference > 0 else "−"
        absolute = self._formatter(abs(difference))
        pct_text = f" · {pct:+.1f}%" if pct is not None else ""
        label = "Improved" if improvement else "Deteriorated"
        self._set_change(
            f"{arrow} {sign}{absolute}{pct_text}\n{label}",
            "positiveChange" if improvement else "negativeChange",
        )

    def _set_change(self, text: str, object_name: str) -> None:
        self.change_label.setText(text)
        self.change_label.setObjectName(object_name)
        self.change_label.style().unpolish(self.change_label)
        self.change_label.style().polish(self.change_label)


def format_currency(value: float | None) -> str:
    if value is None:
        return "N/A"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if magnitude >= 1_000_000_000_000:
        return f"{sign}${magnitude / 1_000_000_000_000:.2f}T"
    if magnitude >= 1_000_000_000:
        return f"{sign}${magnitude / 1_000_000_000:.2f}B"
    return f"{sign}${magnitude:,.0f}"


def format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.1f}%"


def format_units(value: float | None) -> str:
    if value is None:
        return "N/A"
    magnitude = abs(value)
    if magnitude >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f}B"
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    return f"{value:,.0f}"
