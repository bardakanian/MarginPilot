"""Monte Carlo risk controls, summary cards, and histogram."""

from __future__ import annotations

import numpy as np
from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from marginpilot.models.risk_model import RiskConfig, RiskResults
from marginpilot.theme_manager import CHART_THEMES, LIGHT
from marginpilot.widgets.kpi_card import format_currency


class RiskMetric(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("riskMetric")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        name = QLabel(title)
        name.setObjectName("kpiTitle")
        self.value = QLabel("—")
        self.value.setObjectName("riskValue")
        layout.addWidget(name)
        layout.addWidget(self.value)


class RiskPanel(QWidget):
    """Risk analysis tab that requests and displays reproducible simulation."""

    simulationRequested = Signal(object)

    def __init__(self, theme: str = LIGHT) -> None:
        super().__init__()
        self._theme = theme
        self._profits: np.ndarray | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 18)
        root.setSpacing(12)

        heading = QLabel("Monte Carlo Risk Analysis")
        heading.setObjectName("pageTitle")
        explanation = QLabel(
            "Stress-test proposed profit by repeatedly varying sales volume and unit cost. "
            "Uncertainty is treated as a standard deviation around each proposed assumption; "
            "the fixed seed makes every demonstration reproducible."
        )
        explanation.setObjectName("pageIntro")
        explanation.setWordWrap(True)
        root.addWidget(heading)
        root.addWidget(explanation)

        controls = QFrame()
        controls.setObjectName("controlCard")
        controls_layout = QHBoxLayout(controls)
        form = QFormLayout()
        self.volume_uncertainty = QDoubleSpinBox()
        self.volume_uncertainty.setRange(0, 100)
        self.volume_uncertainty.setValue(10)
        self.volume_uncertainty.setSuffix("%")
        self.volume_uncertainty.setToolTip(
            "Standard deviation of simulated sales volume around the proposed volume."
        )
        self.cost_uncertainty = QDoubleSpinBox()
        self.cost_uncertainty.setRange(0, 100)
        self.cost_uncertainty.setValue(5)
        self.cost_uncertainty.setSuffix("%")
        self.cost_uncertainty.setToolTip(
            "Standard deviation of simulated variable cost per unit around the proposal."
        )
        self.simulations = QSpinBox()
        self.simulations.setRange(100, 100_000)
        self.simulations.setSingleStep(1_000)
        self.simulations.setValue(10_000)
        self.simulations.setGroupSeparatorShown(True)
        self.simulations.setToolTip(
            "More simulations create a smoother distribution; 10,000 is suitable for demos."
        )
        form.addRow("Sales-volume uncertainty", self.volume_uncertainty)
        form.addRow("Variable-cost uncertainty", self.cost_uncertainty)
        form.addRow("Number of simulations", self.simulations)
        self.run_button = QPushButton("Run Simulation")
        self.run_button.setObjectName("primaryButton")
        self.run_button.setMinimumWidth(170)
        self.run_button.setToolTip("Run with fixed random seed 42 for reproducible results.")
        self.run_button.clicked.connect(self._request_simulation)
        controls_layout.addLayout(form)
        controls_layout.addStretch()
        controls_layout.addWidget(self.run_button, alignment=Qt.AlignmentFlag.AlignBottom)
        root.addWidget(controls)

        metrics_layout = QHBoxLayout()
        metric_titles = (
            "Chance profit beats current",
            "Chance of a loss",
            "10th percentile",
            "Median profit",
            "90th percentile",
        )
        self.metrics: list[RiskMetric] = []
        for title in metric_titles:
            metric = RiskMetric(title)
            self.metrics.append(metric)
            metrics_layout.addWidget(metric)
        root.addLayout(metrics_layout)

        histogram_card = QFrame()
        histogram_card.setObjectName("chartCard")
        histogram_layout = QVBoxLayout(histogram_card)
        self.histogram = QChartView()
        self.histogram.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.histogram.setMinimumHeight(340)
        histogram_layout.addWidget(self.histogram)
        root.addWidget(histogram_card, 1)
        self._set_empty_chart()

    def _request_simulation(self) -> None:
        self.simulationRequested.emit(
            RiskConfig(
                volume_uncertainty_pct=self.volume_uncertainty.value(),
                variable_cost_uncertainty_pct=self.cost_uncertainty.value(),
                simulations=self.simulations.value(),
                seed=42,
            )
        )

    def update_results(self, results: RiskResults) -> None:
        values = (
            f"{results.probability_beats_current:.1f}%",
            f"{results.probability_of_loss:.1f}%",
            format_currency(results.percentile_10),
            format_currency(results.median),
            format_currency(results.percentile_90),
        )
        for metric, value in zip(self.metrics, values, strict=True):
            metric.value.setText(value)
        self._profits = results.profits.copy()
        self._update_histogram(results.profits)

    def set_theme(self, theme: str) -> None:
        """Repaint the risk chart immediately for an application theme change."""

        self._theme = theme
        if self._profits is None:
            self._set_empty_chart()
        else:
            self._update_histogram(self._profits)

    def _set_empty_chart(self) -> None:
        chart = QChart()
        chart.setTitle("Run the simulation to see the profit distribution")
        _style_chart(chart, self._theme)
        self.histogram.setChart(chart)

    def _update_histogram(self, profits: np.ndarray) -> None:
        counts, edges = np.histogram(profits, bins=24)
        bar_set = QBarSet("Simulation count")
        colors = CHART_THEMES[self._theme]
        bar_set.setColor(QColor(colors.histogram))
        bar_set.setBorderColor(QColor(colors.histogram))
        bar_set.append([float(value) for value in counts])
        series = QBarSeries()
        series.append(bar_set)
        series.setBarWidth(0.92)
        chart = QChart()
        chart.setTitle("Distribution of Simulated Operating Profit")
        _style_chart(chart, self._theme)
        chart.addSeries(series)
        labels = []
        for index in range(len(counts)):
            midpoint = (edges[index] + edges[index + 1]) / 2
            if index % 4 == 0:
                sign = "-" if midpoint < 0 else ""
                label = (
                    f"{sign}${abs(midpoint) / 1_000_000:.1f}m"
                    if abs(midpoint) >= 1_000_000
                    else f"{sign}${abs(midpoint) / 1000:.0f}k"
                )
            else:
                label = "\u200b" * (index + 1)
            labels.append(label)
        x_axis = QBarCategoryAxis()
        x_axis.append(labels)
        x_axis.setTitleText("Operating profit")
        y_axis = QValueAxis()
        y_axis.setRange(0, max(float(counts.max()) * 1.1, 1))
        y_axis.setLabelFormat("%.0f")
        y_axis.setTitleText("Simulations")
        x_axis.setGridLineVisible(False)
        for axis in (x_axis, y_axis):
            axis.setLabelsColor(QColor(colors.secondary_text))
            axis.setTitleBrush(QColor(colors.text))
            axis.setLinePenColor(QColor(colors.axis))
            axis.setGridLineColor(QColor(colors.grid))
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(x_axis)
        series.attachAxis(y_axis)
        chart.legend().setVisible(False)
        self.histogram.setChart(chart)


def _style_chart(chart: QChart, theme: str) -> None:
    colors = CHART_THEMES[theme]
    chart.setTitleBrush(QColor(colors.text))
    chart.setBackgroundVisible(True)
    chart.setBackgroundBrush(QColor(colors.background))
    chart.setPlotAreaBackgroundVisible(True)
    chart.setPlotAreaBackgroundBrush(QColor(colors.plot_background))
