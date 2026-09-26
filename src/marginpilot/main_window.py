"""Main desktop window and presentation orchestration."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStyle,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from marginpilot.models.financial_model import apply_changes, calculate_financials
from marginpilot.models.risk_model import RiskConfig, run_profit_simulation
from marginpilot.services.csv_service import CSVValidationError, load_csv
from marginpilot.theme_manager import DARK, ThemeManager
from marginpilot.widgets.chart_panel import FinancialChartPanel, SensitivityCard
from marginpilot.widgets.glossary_dialog import BusinessGlossaryDialog
from marginpilot.widgets.input_panel import InputPanel
from marginpilot.widgets.kpi_card import (
    KpiCard,
    format_currency,
    format_percent,
    format_units,
)
from marginpilot.widgets.recommendation_panel import RecommendationPanel
from marginpilot.widgets.risk_panel import RiskPanel


class MainWindow(QMainWindow):
    """Professional scenario-planning workspace."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MarginPilot — Interactive Profit Scenario Analyzer")
        self.setMinimumSize(1080, 680)
        self.resize(1440, 900)
        self.project_root = Path(__file__).resolve().parents[2]
        application = QApplication.instance()
        self.theme_manager: ThemeManager = getattr(application, "theme_manager")
        self.glossary_dialog: BusinessGlossaryDialog | None = None

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.setObjectName("workspaceTabs")
        self.workspace_tabs.addTab(self._build_dashboard(), "Dashboard")
        self.risk_panel = RiskPanel(self.theme_manager.theme)
        self.risk_panel.simulationRequested.connect(self.run_simulation)
        self.workspace_tabs.addTab(self.risk_panel, "Risk Analysis")
        root.addWidget(self.workspace_tabs, 1)
        self.setCentralWidget(central)

        self.statusBar().showMessage(
            "Ready • All calculations and imported data stay on this computer"
        )
        self.input_panel.inputsChanged.connect(self.update_dashboard)
        self.theme_manager.themeChanged.connect(self._on_theme_changed)
        self._update_theme_button()
        self.update_dashboard()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("appHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 15, 24, 15)
        layout.setSpacing(10)
        title_column = QVBoxLayout()
        title_column.setSpacing(0)
        title = QLabel("MarginPilot")
        title.setObjectName("appTitle")
        subtitle = QLabel("Interactive Profit Scenario Analyzer")
        subtitle.setObjectName("appSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        layout.addLayout(title_column)
        layout.addStretch()

        self.example_button = QPushButton("Load Example")
        self.example_button.setObjectName("headerPrimaryButton")
        self.example_button.setToolTip("Load the included 12-month fictional sales dataset.")
        self.example_button.setShortcut(QKeySequence("Ctrl+L"))
        self.example_button.clicked.connect(self.load_example)
        self.import_button = QPushButton("Import CSV")
        self.import_button.setObjectName("headerButton")
        self.import_button.setToolTip("Import a local CSV file; no data is uploaded.")
        self.import_button.setShortcut(QKeySequence("Ctrl+I"))
        self.import_button.clicked.connect(self.import_csv_dialog)

        self.glossary_button = QPushButton("Explain Terms")
        self.glossary_button.setObjectName("headerButton")
        self.glossary_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.glossary_button.setToolTip(
            "Open plain-language definitions and formulas (Ctrl+E)."
        )
        self.glossary_button.setShortcut(QKeySequence("Ctrl+E"))
        self.glossary_button.clicked.connect(self.open_glossary)

        self.theme_button = QPushButton()
        self.theme_button.setObjectName("headerButton")
        self.theme_button.setToolTip(
            "Switch between Light and Dark modes. Your selection is remembered (Ctrl+T)."
        )
        self.theme_button.setShortcut(QKeySequence("Ctrl+T"))
        self.theme_button.clicked.connect(self.theme_manager.toggle)

        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("headerButton")
        self.reset_button.setToolTip("Restore the default baseline and zero all scenario changes.")
        self.reset_button.setShortcut(QKeySequence("Ctrl+R"))
        self.reset_button.clicked.connect(self.reset_application)
        layout.addWidget(self.example_button)
        layout.addWidget(self.import_button)
        layout.addWidget(self.glossary_button)
        layout.addWidget(self.theme_button)
        layout.addWidget(self.reset_button)
        return header

    def _build_dashboard(self) -> QWidget:
        dashboard = QWidget()
        dashboard_layout = QHBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(16, 14, 16, 16)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        input_scroll = QScrollArea()
        input_scroll.setObjectName("inputScroll")
        input_scroll.setWidgetResizable(True)
        input_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.input_panel = InputPanel()
        input_scroll.setWidget(self.input_panel)
        input_scroll.setMinimumWidth(370)
        input_scroll.setMaximumWidth(470)
        splitter.addWidget(input_scroll)

        content_scroll = QScrollArea()
        content_scroll.setObjectName("contentScroll")
        content_scroll.setWidgetResizable(True)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 0, 0, 0)
        content_layout.setSpacing(12)

        intro_row = QHBoxLayout()
        intro_column = QVBoxLayout()
        page_title = QLabel("Scenario dashboard")
        page_title.setObjectName("pageTitle")
        page_intro = QLabel(
            "Compare today's baseline with a proposed pricing, demand, and cost plan."
        )
        page_intro.setObjectName("pageIntro")
        intro_column.addWidget(page_title)
        intro_column.addWidget(page_intro)
        self.scenario_badge = QLabel("BASELINE")
        self.scenario_badge.setObjectName("scenarioBadge")
        intro_row.addLayout(intro_column)
        intro_row.addStretch()
        intro_row.addWidget(self.scenario_badge, alignment=Qt.AlignmentFlag.AlignTop)
        content_layout.addLayout(intro_row)

        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(9)
        self.kpi_cards = {
            "revenue": KpiCard("Revenue", format_currency),
            "total_costs": KpiCard("Total costs", format_currency, lower_is_better=True),
            "operating_profit": KpiCard("Operating profit", format_currency),
            "profit_margin": KpiCard("Profit margin", format_percent),
            "break_even_units": KpiCard("Break-even units", format_units, lower_is_better=True),
        }
        for card in self.kpi_cards.values():
            kpi_layout.addWidget(card)
        content_layout.addLayout(kpi_layout)

        chart_layout = QHBoxLayout()
        chart_layout.setSpacing(12)
        self.comparison_chart = FinancialChartPanel(self.theme_manager.theme)
        self.sensitivity_chart = SensitivityCard(self.theme_manager.theme)
        chart_layout.addWidget(self.comparison_chart, 1)
        chart_layout.addWidget(self.sensitivity_chart, 1)
        content_layout.addLayout(chart_layout)

        self.recommendation = RecommendationPanel()
        content_layout.addWidget(self.recommendation)
        content_scroll.setWidget(content)
        splitter.addWidget(content_scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([390, 1000])
        dashboard_layout.addWidget(splitter)
        return dashboard

    def update_dashboard(self) -> None:
        """Recalculate and repaint every dashboard component."""

        baseline = self.input_panel.baseline()
        changes = self.input_panel.changes()
        proposed_inputs = apply_changes(baseline, changes)
        self.input_panel.update_scenario_values(baseline, proposed_inputs)
        current = calculate_financials(baseline)
        proposed = calculate_financials(proposed_inputs)
        self.kpi_cards["revenue"].update_values(current.revenue, proposed.revenue)
        self.kpi_cards["total_costs"].update_values(
            current.total_costs, proposed.total_costs
        )
        self.kpi_cards["operating_profit"].update_values(
            current.operating_profit, proposed.operating_profit
        )
        self.kpi_cards["profit_margin"].update_values(
            current.profit_margin, proposed.profit_margin
        )
        self.kpi_cards["break_even_units"].update_values(
            current.break_even_units, proposed.break_even_units
        )
        self.comparison_chart.update_comparison(current, proposed)
        self.sensitivity_chart.update_chart(baseline, changes)
        self.recommendation.update_recommendation(
            baseline, proposed_inputs, current, proposed
        )
        active = any(
            abs(value) > 0.0001
            for value in (
                changes.price,
                changes.volume,
                changes.variable_cost,
                changes.fixed_cost,
                changes.marketing,
            )
        )
        self.scenario_badge.setText("ACTIVE SCENARIO" if active else "BASELINE")

    def import_csv_dialog(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Import operating data",
            str(self.project_root),
            "CSV files (*.csv);;All files (*)",
        )
        if path:
            self.load_csv_path(path)

    def load_csv_path(self, path: str | Path) -> bool:
        """Load a CSV path, returning whether import succeeded."""

        try:
            imported = load_csv(path)
        except CSVValidationError as exc:
            QMessageBox.warning(self, "CSV import problem", str(exc))
            self.statusBar().showMessage("CSV import failed • Review the file and try again")
            return False
        self.input_panel.set_imported_data(imported)
        self.workspace_tabs.setCurrentIndex(0)
        self.statusBar().showMessage(
            f"Loaded {imported.source.name} • {len(imported.dataframe)} rows aggregated into the baseline"
        )
        return True

    def load_example(self) -> None:
        example = self.project_root / "sample_data" / "example_sales.csv"
        self.load_csv_path(example)

    def reset_application(self) -> None:
        self.input_panel.reset_all()
        self.workspace_tabs.setCurrentIndex(0)
        self.statusBar().showMessage("Reset complete • Default manual baseline restored")

    def open_glossary(self) -> None:
        """Open a single non-editable glossary dialog without blocking updates."""

        if self.glossary_dialog is None:
            self.glossary_dialog = BusinessGlossaryDialog(self)
            self.glossary_dialog.finished.connect(self._clear_glossary_reference)
        self.glossary_dialog.open()
        self.glossary_dialog.raise_()
        self.glossary_dialog.activateWindow()

    def _clear_glossary_reference(self, _result: int) -> None:
        if self.glossary_dialog is not None:
            self.glossary_dialog.deleteLater()
        self.glossary_dialog = None

    def _on_theme_changed(self, theme: str) -> None:
        """Refresh QSS-driven labels and every active Qt chart."""

        self._update_theme_button()
        self.comparison_chart.set_theme(theme)
        self.sensitivity_chart.set_theme(theme)
        self.risk_panel.set_theme(theme)
        self.update_dashboard()
        self.statusBar().showMessage(
            f"{theme.title()} mode applied • Charts and controls updated"
        )

    def _update_theme_button(self) -> None:
        current = "Dark" if self.theme_manager.theme == DARK else "Light"
        self.theme_button.setText(f"Theme: {current}")
        self.theme_button.setAccessibleName(
            f"Current theme is {current}. Activate to switch themes."
        )

    def run_simulation(self, config: RiskConfig | None = None) -> None:
        """Run and display risk simulation for the current proposed scenario."""

        if config is None:
            config = RiskConfig()
        baseline = self.input_panel.baseline()
        proposed = apply_changes(baseline, self.input_panel.changes())
        results = run_profit_simulation(baseline, proposed, config)
        self.risk_panel.update_results(results)
        self.statusBar().showMessage(
            f"Risk simulation complete • {config.simulations:,} trials • fixed seed {config.seed}"
        )
