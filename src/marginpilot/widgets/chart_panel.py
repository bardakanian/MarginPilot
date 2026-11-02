"""Dynamic QtCharts visualizations for the scenario dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, log10

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QCategoryAxis,
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
    best_price_change,
    calculate_financials,
    price_sensitivity,
)
from marginpilot.theme_manager import CHART_THEMES, LIGHT
from marginpilot.widgets.kpi_card import format_currency

SENSITIVITY_RANGE = (-20.0, 20.0)


class FinancialChartPanel(QFrame):
    """Grouped bar chart comparing current and proposed results."""

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
        scale = currency_scale(current_raw + proposed_raw)
        current_values = [value / scale.divisor for value in current_raw]
        proposed_values = [value / scale.divisor for value in proposed_raw]
        current_set.append(current_values)
        proposed_set.append(proposed_values)
        series = QBarSeries()
        series.append(current_set)
        series.append(proposed_set)
        series.setBarWidth(0.88)
        series.setLabelsVisible(True)
        # QtCharts cannot put a minus sign before "$", so negative values drop
        # the symbol; the axis title still names the currency.
        has_negative = min(current_values + proposed_values) < 0
        prefix = "" if has_negative else "$"
        series.setLabelsFormat(f"{prefix}@value{scale.suffix}")
        series.setLabelsPrecision(3)
        series.setLabelsPosition(QBarSeries.LabelsPosition.LabelsOutsideEnd)
        chart.addSeries(series)

        category_axis = QBarCategoryAxis()
        category_axis.append(["Revenue", "Total costs", "Op. profit"])
        low = min(0.0, *current_values, *proposed_values)
        high = max(0.0, *current_values, *proposed_values)
        # Headroom keeps the outside-end labels inside the plot area.
        span = high - low
        value_axis = _money_axis(
            low - (span * 0.12 if low < 0 else 0.0), high + span * 0.14, scale
        )
        _style_axis(category_axis, self._theme)
        _style_axis(value_axis, self._theme)
        chart.addAxis(category_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(value_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(category_axis)
        series.attachAxis(value_axis)
        _show_legend(chart, self._theme)
        self.chart_view.setChart(chart)


class SensitivityCard(QFrame):
    """Profit across a price range, with demand response when elasticity is set."""

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
        self.note = QLabel()
        self.note.setObjectName("chartNote")
        self.note.setWordWrap(True)
        layout.addWidget(self.chart_view)
        layout.addWidget(self.note)

    def set_theme(self, theme: str) -> None:
        self._theme = theme

    def update_chart(self, baseline: FinancialInputs, changes: ScenarioChanges) -> None:
        colors = CHART_THEMES[self._theme]
        chart = _base_chart("Profit Sensitivity to Price", self._theme)
        points = price_sensitivity(
            baseline, changes, low=SENSITIVITY_RANGE[0], high=SENSITIVITY_RANGE[1]
        )
        best = best_price_change(points)
        selected_profit = calculate_financials(
            apply_changes(baseline, changes)
        ).operating_profit
        scale = currency_scale(
            [point.operating_profit for point in points] + [selected_profit]
        )

        line = QLineSeries()
        line.setName("Projected profit")
        line.setPen(QPen(QColor(colors.line), 2.5))
        for point in points:
            line.append(point.price_change, point.operating_profit / scale.divisor)
        chart.addSeries(line)
        added: list[QLineSeries | QScatterSeries] = [line]

        demand_responds = changes.price_elasticity != 0
        if demand_responds:
            optimum = QScatterSeries()
            optimum.setName(f"Best in range ({best.price_change:+.1f}%)")
            optimum.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeRectangle)
            optimum.setColor(QColor(colors.background))
            optimum.setBorderColor(QColor(colors.line))
            optimum.setPen(QPen(QColor(colors.line), 2.5))
            optimum.setMarkerSize(12)
            optimum.append(QPointF(best.price_change, best.operating_profit / scale.divisor))
            chart.addSeries(optimum)
            added.append(optimum)

        selected = QScatterSeries()
        selected.setName(f"Selected ({changes.price:+.1f}%)")
        selected.setColor(QColor(colors.marker))
        selected.setBorderColor(QColor(colors.marker_border))
        selected.setMarkerSize(13)
        selected.append(QPointF(changes.price, selected_profit / scale.divisor))
        chart.addSeries(selected)
        added.append(selected)

        profits = [point.operating_profit / scale.divisor for point in points]
        low = min(*profits, selected_profit / scale.divisor)
        high = max(*profits, selected_profit / scale.divisor)
        padding = max((high - low) * 0.12, abs(high) * 0.05, 1e-9)
        y_axis = _money_axis(low - padding, high + padding, scale)
        if y_axis.min() < 0 < y_axis.max():
            zero = QLineSeries()
            zero.setName("Break-even")
            zero.setPen(QPen(QColor(colors.zero), 1.2, Qt.PenStyle.DashLine))
            zero.append(SENSITIVITY_RANGE[0], 0.0)
            zero.append(SENSITIVITY_RANGE[1], 0.0)
            chart.addSeries(zero)
            added.append(zero)

        x_axis = QValueAxis()
        x_axis.setRange(*SENSITIVITY_RANGE)
        x_axis.setTickCount(5)
        x_axis.setLabelFormat("%+.0f%%")
        x_axis.setTitleText("Price change")
        _style_axis(x_axis, self._theme)
        _style_axis(y_axis, self._theme)
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        for series in added:
            series.attachAxis(x_axis)
            series.attachAxis(y_axis)
        _show_legend(chart, self._theme)
        self.chart_view.setChart(chart)
        self.note.setText(sensitivity_note(changes, best.price_change, best.operating_profit))


def sensitivity_note(
    changes: ScenarioChanges, best_change: float, best_profit: float
) -> str:
    """Explain what the sensitivity curve holds constant and what it implies."""

    if changes.price_elasticity == 0:
        return (
            "Price elasticity is off, so volume ignores price and profit rises in a "
            "straight line. Set an elasticity to model customers' response."
        )
    return (
        f"Volume responds to price (elasticity {changes.price_elasticity:.1f}). "
        f"Most profitable price change in range: {best_change:+.1f}%, "
        f"{format_currency(best_profit)} operating profit."
    )


@dataclass(frozen=True, slots=True)
class CurrencyScale:
    """Divisor and labels for showing money in thousands, millions or billions."""

    divisor: float
    suffix: str
    unit_name: str

    def label(self, scaled_value: float, decimals: int) -> str:
        if abs(scaled_value) < 10 ** -(decimals + 1):
            scaled_value = 0.0
        sign = "-" if scaled_value < 0 else ""
        return f"{sign}${abs(scaled_value):,.{decimals}f}{self.suffix}"


def currency_scale(values: list[float]) -> CurrencyScale:
    maximum = max((abs(value) for value in values), default=0.0)
    if maximum >= 1_000_000_000:
        return CurrencyScale(1_000_000_000.0, "B", "billions")
    if maximum >= 1_000_000:
        return CurrencyScale(1_000_000.0, "M", "millions")
    if maximum >= 1_000:
        return CurrencyScale(1_000.0, "k", "thousands")
    return CurrencyScale(1.0, "", "dollars")


def nice_ticks(low: float, high: float, target: int = 5) -> tuple[float, float, float]:
    """Round an axis range out to tick steps of 1, 2, 2.5 or 5 × 10ⁿ.

    Returns ``(start, stop, step)`` covering ``low``..``high``.
    """

    if high < low:
        low, high = high, low
    if high - low < 1e-12:
        high = low + 1.0
    raw_step = (high - low) / max(target, 1)
    magnitude = 10 ** floor(log10(raw_step))
    step = next(
        multiple * magnitude
        for multiple in (1.0, 2.0, 2.5, 5.0, 10.0)
        if multiple * magnitude >= raw_step
    )
    start = floor(low / step + 1e-9) * step
    stop = ceil(high / step - 1e-9) * step
    return start, stop, step


def tick_decimals(step: float) -> int:
    """Decimals needed to show every multiple of ``step`` exactly."""

    for decimals in range(4):
        if abs(step * 10**decimals - round(step * 10**decimals)) < 1e-9:
            return decimals
    return 4


def _money_axis(low: float, high: float, scale: CurrencyScale) -> QCategoryAxis:
    """A value axis with round ticks and correctly signed currency labels."""

    start, stop, step = nice_ticks(low, high)
    decimals = tick_decimals(step)
    axis = QCategoryAxis()
    axis.setLabelsPosition(QCategoryAxis.AxisLabelsPosition.AxisLabelsPositionOnValue)
    axis.setStartValue(start)
    count = round((stop - start) / step)
    for index in range(count + 1):
        value = start + index * step
        axis.append(scale.label(value, decimals), value)
    axis.setRange(start, stop)
    axis.setTitleText(f"USD ({scale.unit_name})")
    return axis


def _base_chart(title: str, theme: str) -> QChart:
    colors = CHART_THEMES[theme]
    chart = QChart()
    chart.setTitle(title)
    chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
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


def _show_legend(chart: QChart, theme: str) -> None:
    chart.legend().setVisible(True)
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
    chart.legend().setLabelColor(QColor(CHART_THEMES[theme].text))


def _style_axis(axis: QValueAxis | QBarCategoryAxis | QCategoryAxis, theme: str) -> None:
    colors = CHART_THEMES[theme]
    axis.setLabelsColor(QColor(colors.secondary_text))
    axis.setTitleBrush(QColor(colors.text))
    axis.setGridLineColor(QColor(colors.grid))
    axis.setLinePenColor(QColor(colors.axis))
