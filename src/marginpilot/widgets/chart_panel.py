"""Dynamic QtCharts visualizations for the scenario dashboard."""

from __future__ import annotations

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QScatterSeries,
    QValueAxis,
)
from PySide6.QtCore import QMargins, QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout

from marginpilot.models.financial_model import (
    FinancialInputs,
    FinancialResults,
    ScenarioChanges,
    apply_changes,
    calculate_financials,
)
from marginpilot.theme_manager import CHART_THEMES, LIGHT


class FinancialChartPanel(QFrame):
    """Side-by-side financial comparison and price sensitivity charts."""

    def __init__(self, theme: str = LIGHT) -> None:
        super().__init__()
        self._theme = theme
        self.setObjectName("chartCard")
        self.setMinimumHeight(345)
        self.setMaximumHeight(405)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 6)
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(285)
        layout.addWidget(self.chart_view)

    def set_theme(self, theme: str) -> None:
        self._theme = theme

    def update_comparison(
        self, current: FinancialResults, proposed: FinancialResults
    ) -> None:
        colors = CHART_THEMES[self._theme]
        chart = _base_chart("Current vs. Proposed", self._theme)
        chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        current_set = QBarSet("Current")
        current_set.setColor(QColor(colors.current))
        current_set.setBorderColor(QColor(colors.current))
        current_set.setLabelColor(QColor(colors.text))
        proposed_set = QBarSet("Proposed")
        proposed_set.setColor(QColor(colors.proposed))
        proposed_set.setBorderColor(QColor(colors.proposed))
        proposed_set.setLabelColor(QColor(colors.text))
        current_raw = [current.revenue, current.total_costs, current.operating_profit]
        proposed_raw = [proposed.revenue, proposed.total_costs, proposed.operating_profit]
        divisor, unit_name, axis_format, label_suffix = _currency_scale(
            current_raw + proposed_raw
        )
        current_values = [value / divisor for value in current_raw]
        proposed_values = [value / divisor for value in proposed_raw]
        current_set.append(current_values)
        proposed_set.append(proposed_values)
        series = QBarSeries()
        series.append(current_set)
        series.append(proposed_set)
        series.setBarWidth(0.88)
        series.setLabelsVisible(True)
        series.setLabelsFormat(f"$@value{label_suffix}")
        series.setLabelsPrecision(3)
        series.setLabelsPosition(QBarSeries.LabelsPosition.LabelsOutsideEnd)
        chart.addSeries(series)

        category_axis = QBarCategoryAxis()
        category_axis.append(["Revenue", "Total costs", "Op. profit"])
        value_axis = QValueAxis()
        low = min(0.0, *current_values, *proposed_values)
        high = max(0.0, *current_values, *proposed_values)
        padding = max((high - low) * 0.16, 1.0)
        value_axis.setRange(low - (padding if low < 0 else 0), high + padding)
        value_axis.setLabelFormat(axis_format)
        value_axis.setTitleText(f"USD ({unit_name})")
        value_axis.setTickCount(6)
        _style_axis(category_axis, self._theme)
        _style_axis(value_axis, self._theme)
        chart.addAxis(category_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(value_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(category_axis)
        series.attachAxis(value_axis)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.legend().setLabelColor(QColor(colors.text))
        self.chart_view.setChart(chart)

    def update_sensitivity(
        self, baseline: FinancialInputs, changes: ScenarioChanges
    ) -> None:
        colors = CHART_THEMES[self._theme]
        chart = _base_chart("Profit Sensitivity to Price", self._theme)
        line = QLineSeries()
        line.setName("Projected profit")
        line.setColor(QColor(colors.line))
        line.setPen(QPen(QColor(colors.line), 2.5))
        raw_points: list[tuple[float, float]] = []
        for price_change in range(-20, 21):
            varied = ScenarioChanges(
                price=float(price_change),
                volume=changes.volume,
                variable_cost=changes.variable_cost,
                fixed_cost=changes.fixed_cost,
                marketing=changes.marketing,
            )
            profit = calculate_financials(apply_changes(baseline, varied)).operating_profit
            raw_points.append((float(price_change), profit))

        selected_profit = calculate_financials(
            apply_changes(baseline, changes)
        ).operating_profit
        divisor, unit_name, axis_format, _label_suffix = _currency_scale(
            [profit for _price, profit in raw_points] + [selected_profit]
        )
        profits = [profit / divisor for _price, profit in raw_points]
        for price_change, profit in raw_points:
            line.append(price_change, profit / divisor)
        chart.addSeries(line)
        selected = QScatterSeries()
        selected.setName(f"Selected ({changes.price:+.1f}%)")
        selected.setColor(QColor(colors.marker))
        selected.setBorderColor(QColor(colors.marker_border))
        selected.setMarkerSize(13)
        selected.append(QPointF(changes.price, selected_profit / divisor))
        chart.addSeries(selected)

        x_axis = QValueAxis()
        x_axis.setRange(-20, 20)
        x_axis.setTickCount(5)
        x_axis.setLabelFormat("%+.0f%%")
        x_axis.setTitleText("Price change")
        y_axis = QValueAxis()
        selected_profit_scaled = selected_profit / divisor
        low = min(0.0, *profits, selected_profit_scaled)
        high = max(0.0, *profits, selected_profit_scaled)
        padding = max((high - low) * 0.12, 1.0)
        y_axis.setRange(low - padding, high + padding)
        y_axis.setTickCount(6)
        y_axis.setLabelFormat(axis_format)
        y_axis.setTitleText(f"USD ({unit_name})")
        _style_axis(x_axis, self._theme)
        _style_axis(y_axis, self._theme)
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        line.attachAxis(x_axis)
        line.attachAxis(y_axis)
        selected.attachAxis(x_axis)
        selected.attachAxis(y_axis)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.legend().setLabelColor(QColor(colors.text))
        self.chart_view.setChart(chart)


class SensitivityCard(QFrame):
    """Sensitivity chart with an explicit constant-assumptions note."""

    def __init__(self, theme: str = LIGHT) -> None:
        super().__init__()
        self._theme = theme
        self.setObjectName("chartCard")
        self.setMinimumHeight(345)
        self.setMaximumHeight(405)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 6)
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(250)
        note = QLabel(
            "Volume, variable cost, fixed cost, and marketing assumptions remain "
            "constant across the price range."
        )
        note.setObjectName("chartNote")
        note.setWordWrap(True)
        layout.addWidget(self.chart_view)
        layout.addWidget(note)

    def update_chart(self, baseline: FinancialInputs, changes: ScenarioChanges) -> None:
        helper = FinancialChartPanel(self._theme)
        helper.chart_view = self.chart_view
        helper.update_sensitivity(baseline, changes)
        helper.deleteLater()

    def set_theme(self, theme: str) -> None:
        self._theme = theme


def _base_chart(title: str, theme: str) -> QChart:
    colors = CHART_THEMES[theme]
    chart = QChart()
    chart.setTitle(title)
    title_font = QFont(QApplication.font())
    title_font.setPointSize(12)
    title_font.setBold(True)
    chart.setTitleFont(title_font)
    chart.setTitleBrush(QColor(colors.text))
    chart.setBackgroundVisible(True)
    chart.setBackgroundBrush(QColor(colors.background))
    chart.setBackgroundPen(QPen(QColor(colors.background)))
    chart.setPlotAreaBackgroundVisible(True)
    chart.setPlotAreaBackgroundBrush(QColor(colors.plot_background))
    chart.setMargins(QMargins(4, 4, 4, 4))
    return chart


def _style_axis(axis: QValueAxis | QBarCategoryAxis, theme: str) -> None:
    colors = CHART_THEMES[theme]
    axis.setLabelsColor(QColor(colors.secondary_text))
    axis.setTitleBrush(QColor(colors.text))
    axis.setGridLineColor(QColor(colors.grid))
    axis.setLinePenColor(QColor(colors.axis))


def _currency_scale(values: list[float]) -> tuple[float, str, str, str]:
    maximum = max((abs(value) for value in values), default=0.0)
    if maximum >= 1_000_000_000:
        return 1_000_000_000.0, "billions", "$%.1fB", "B"
    if maximum >= 1_000_000:
        return 1_000_000.0, "millions", "$%.1fM", "M"
    if maximum >= 1_000:
        return 1_000.0, "thousands", "$%.0fk", "k"
    return 1.0, "dollars", "$%.0f", ""
