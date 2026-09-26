"""Baseline entry, CSV preview, and synchronized scenario controls."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from marginpilot.models.financial_model import FinancialInputs, ScenarioChanges
from marginpilot.services.csv_service import ImportedData


class DataFrameTableModel(QAbstractTableModel):
    """Read-only Qt model that preserves and displays imported pandas data."""

    def __init__(self) -> None:
        super().__init__()
        self._dataframe = pd.DataFrame()

    def set_dataframe(self, dataframe: pd.DataFrame) -> None:
        self.beginResetModel()
        self._dataframe = dataframe.copy()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._dataframe)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._dataframe.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        value = self._dataframe.iat[index.row(), index.column()]
        if isinstance(value, float):
            return f"{value:,.2f}"
        return str(value)

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._dataframe.columns[section]).replace("_", " ").title()
        return str(section + 1)


class ScenarioControl(QFrame):
    """A slider and spin box that remain synchronized without signal loops."""

    valueChanged = Signal(float)

    def __init__(
        self,
        label: str,
        minimum: int,
        maximum: int,
        tooltip: str,
        value_type: Literal["currency", "units"],
    ) -> None:
        super().__init__()
        self.setObjectName("scenarioControl")
        self._value_type = value_type
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 5)
        layout.setSpacing(3)

        top = QHBoxLayout()
        name = QLabel(label)
        name.setObjectName("fieldLabel")
        name.setToolTip(tooltip)
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setDecimals(1)
        self.spin.setSingleStep(0.5)
        self.spin.setSuffix("%")
        self.spin.setFixedWidth(82)
        self.spin.setAccessibleName(f"{label} percentage change")
        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("smallButton")
        self.reset_button.setFixedWidth(52)
        self.reset_button.setToolTip(f"Reset {label.lower()} change to zero percent")
        top.addWidget(name)
        top.addStretch()
        top.addWidget(self.spin)
        top.addWidget(self.reset_button)

        self.value_flow = QLabel("Current —  →  Proposed —")
        self.value_flow.setObjectName("valueFlow")
        self.value_flow.setToolTip(tooltip)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum * 10, maximum * 10)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setToolTip(tooltip)
        self.slider.setAccessibleName(f"{label} percentage change slider")
        layout.addLayout(top)
        layout.addWidget(self.value_flow)
        layout.addWidget(self.slider)

        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)
        self.reset_button.clicked.connect(lambda: self.set_value(0.0, emit=True))

    def _from_slider(self, value: int) -> None:
        number = value / 10.0
        with QSignalBlocker(self.spin):
            self.spin.setValue(number)
        self.valueChanged.emit(number)

    def _from_spin(self, value: float) -> None:
        with QSignalBlocker(self.slider):
            self.slider.setValue(round(value * 10))
        self.valueChanged.emit(value)

    def set_value(self, value: float, *, emit: bool = False) -> None:
        with QSignalBlocker(self.slider), QSignalBlocker(self.spin):
            self.slider.setValue(round(value * 10))
            self.spin.setValue(value)
        if emit:
            self.valueChanged.emit(value)

    def value(self) -> float:
        return self.spin.value()

    def set_comparison(self, current: float, proposed: float) -> None:
        """Show the current and proposed business value for this driver."""

        if self._value_type == "units":
            current_text = f"{current:,.0f} units"
            proposed_text = f"{proposed:,.0f} units"
        elif abs(current) < 1_000 and abs(proposed) < 1_000:
            current_text = f"${current:,.2f}"
            proposed_text = f"${proposed:,.2f}"
        else:
            current_text = f"${current:,.0f}"
            proposed_text = f"${proposed:,.0f}"
        self.value_flow.setText(f"{current_text}  →  {proposed_text}")


class InputPanel(QFrame):
    """Complete input section for manual and imported baselines."""

    inputsChanged = Signal()

    DEFAULTS = FinancialInputs(
        units_sold=10_000,
        price_per_unit=50.0,
        variable_cost_per_unit=28.0,
        fixed_costs=120_000,
        marketing_spend=40_000,
    )

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("inputPanel")
        self.setMinimumWidth(350)
        self.imported_data: ImportedData | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        title = QLabel("Current Business Inputs")
        title.setObjectName("sectionTitle")
        helper = QLabel("Set a baseline, then test a proposed scenario.")
        helper.setObjectName("mutedLabel")
        root.addWidget(title)
        root.addWidget(helper)

        self.mode_tabs = QTabWidget()
        self.mode_tabs.setObjectName("modeTabs")
        self.mode_tabs.addTab(self._build_manual_tab(), "Manual Entry")
        self.mode_tabs.addTab(self._build_csv_tab(), "CSV Import")
        self.mode_tabs.setMinimumHeight(238)
        root.addWidget(self.mode_tabs)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(divider)
        scenario_title = QLabel("Scenario Assumptions")
        scenario_title.setObjectName("sectionTitle")
        root.addWidget(scenario_title)

        specifications: Sequence[
            tuple[str, int, int, str, str, Literal["currency", "units"], str]
        ] = (
            ("Selling price", -20, 20, "price", "Adjust the amount charged for each unit. This is a scenario assumption, not a guaranteed customer response.", "currency", "Revenue Drivers"),
            ("Sales volume", -30, 30, "volume", "Adjust the number of units expected to sell during the selected period.", "units", "Revenue Drivers"),
            ("Unit cost", -20, 20, "variable_cost", "Adjust the variable cost incurred for each additional unit.", "currency", "Cost Drivers"),
            ("Fixed costs", -20, 20, "fixed_cost", "Adjust fixed operating costs for the selected period.", "currency", "Cost Drivers"),
            ("Marketing spend", -50, 100, "marketing", "Adjust planned marketing investment without assuming that it causes a specific sales result.", "currency", "Cost Drivers"),
        )
        self.scenario_controls: dict[str, ScenarioControl] = {}
        current_group = ""
        for label, minimum, maximum, key, tooltip, value_type, group in specifications:
            if group != current_group:
                group_label = QLabel(group)
                group_label.setObjectName("driverGroupTitle")
                root.addWidget(group_label)
                current_group = group
            control = ScenarioControl(
                label, minimum, maximum, tooltip, value_type
            )
            control.valueChanged.connect(lambda _value: self.inputsChanged.emit())
            self.scenario_controls[key] = control
            root.addWidget(control)
        root.addStretch()

        self.set_baseline(self.DEFAULTS)

    def _build_manual_tab(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(4, 10, 4, 8)
        layout.setSpacing(8)
        self.units = self._number_input(0, 10_000_000, 0, " units")
        self.price = self._number_input(0, 1_000_000, 2, "", "$")
        self.variable_cost = self._number_input(0, 1_000_000, 2, "", "$")
        self.fixed_costs = self._number_input(0, 1_000_000_000, 2, "", "$")
        self.marketing = self._number_input(0, 1_000_000_000, 2, "", "$")
        fields = (
            ("Units sold", self.units),
            ("Selling price / unit", self.price),
            ("Variable cost / unit", self.variable_cost),
            ("Fixed operating costs", self.fixed_costs),
            ("Marketing spend", self.marketing),
        )
        for label, widget in fields:
            layout.addRow(label, widget)
            widget.valueChanged.connect(lambda _value: self.inputsChanged.emit())
        return page

    def _build_csv_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 10, 4, 4)
        self.csv_status = QLabel("No CSV loaded. Use Import CSV or Load Example.")
        self.csv_status.setObjectName("emptyState")
        self.csv_status.setWordWrap(True)
        self.table_model = DataFrameTableModel()
        self.preview = QTableView()
        self.preview.setModel(self.table_model)
        self.preview.setAlternatingRowColors(True)
        self.preview.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.preview.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.preview.verticalHeader().setDefaultSectionSize(24)
        layout.addWidget(self.csv_status)
        layout.addWidget(self.preview, 1)
        return page

    @staticmethod
    def _number_input(
        minimum: float,
        maximum: float,
        decimals: int,
        suffix: str = "",
        prefix: str = "",
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setDecimals(decimals)
        widget.setGroupSeparatorShown(True)
        widget.setPrefix(prefix)
        widget.setSuffix(suffix)
        widget.setAlignment(Qt.AlignmentFlag.AlignRight)
        return widget

    def baseline(self) -> FinancialInputs:
        return FinancialInputs(
            units_sold=self.units.value(),
            price_per_unit=self.price.value(),
            variable_cost_per_unit=self.variable_cost.value(),
            fixed_costs=self.fixed_costs.value(),
            marketing_spend=self.marketing.value(),
        )

    def changes(self) -> ScenarioChanges:
        return ScenarioChanges(
            price=self.scenario_controls["price"].value(),
            volume=self.scenario_controls["volume"].value(),
            variable_cost=self.scenario_controls["variable_cost"].value(),
            fixed_cost=self.scenario_controls["fixed_cost"].value(),
            marketing=self.scenario_controls["marketing"].value(),
        )

    def update_scenario_values(
        self, baseline: FinancialInputs, proposed: FinancialInputs
    ) -> None:
        """Refresh every current-to-proposed value displayed beside the sliders."""

        comparisons = {
            "price": (baseline.price_per_unit, proposed.price_per_unit),
            "volume": (baseline.units_sold, proposed.units_sold),
            "variable_cost": (
                baseline.variable_cost_per_unit,
                proposed.variable_cost_per_unit,
            ),
            "fixed_cost": (baseline.fixed_costs, proposed.fixed_costs),
            "marketing": (baseline.marketing_spend, proposed.marketing_spend),
        }
        for key, values in comparisons.items():
            self.scenario_controls[key].set_comparison(*values)

    def set_baseline(self, baseline: FinancialInputs) -> None:
        widgets_and_values = (
            (self.units, baseline.units_sold),
            (self.price, baseline.price_per_unit),
            (self.variable_cost, baseline.variable_cost_per_unit),
            (self.fixed_costs, baseline.fixed_costs),
            (self.marketing, baseline.marketing_spend),
        )
        for widget, value in widgets_and_values:
            with QSignalBlocker(widget):
                widget.setValue(value)
        self.inputsChanged.emit()

    def set_imported_data(self, imported: ImportedData) -> None:
        self.imported_data = imported
        self.table_model.set_dataframe(imported.dataframe)
        self.csv_status.setText(
            f"Loaded {imported.source.name}  •  {len(imported.dataframe)} rows  •  "
            f"{imported.baseline.units_sold:,.0f} total units"
        )
        self.csv_status.setObjectName("successState")
        self.csv_status.style().unpolish(self.csv_status)
        self.csv_status.style().polish(self.csv_status)
        self.preview.resizeColumnsToContents()
        self.set_baseline(imported.baseline)
        self.mode_tabs.setCurrentIndex(1)

    def reset_all(self) -> None:
        self.imported_data = None
        self.table_model.set_dataframe(pd.DataFrame())
        self.csv_status.setText("No CSV loaded. Use Import CSV or Load Example.")
        self.csv_status.setObjectName("emptyState")
        self.mode_tabs.setCurrentIndex(0)
        for control in self.scenario_controls.values():
            control.set_value(0.0)
        self.set_baseline(self.DEFAULTS)
