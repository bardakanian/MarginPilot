"""Scrollable, read-only business glossary dialog."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

GlossaryEntry = tuple[str, str, str | None]


SECTIONS: Sequence[tuple[str, Sequence[GlossaryEntry]]] = (
    (
        "BUSINESS INPUTS",
        (
            ("Units sold", "The number of products the business expects to sell during the selected period.", None),
            ("Selling price per unit", "The amount charged to the customer for one unit.", None),
            ("Variable cost per unit", "The cost associated with producing or purchasing one additional unit.", None),
            ("Fixed operating costs", "Expenses that generally remain unchanged when sales volume changes, such as rent, salaries, insurance, and software subscriptions.", None),
            ("Marketing spend", "The amount allocated to advertising, promotions, and customer acquisition.", None),
        ),
    ),
    (
        "FINANCIAL RESULTS",
        (
            ("Revenue", "The total income generated from sales.", "Units sold × selling price per unit"),
            ("Variable costs", "The combined variable cost of all units sold.", "Units sold × variable cost per unit"),
            ("Total costs", "The combined variable costs, fixed operating costs, and marketing spending.", "Variable costs + fixed costs + marketing spend"),
            ("Operating profit", "The estimated amount remaining after the modeled operating costs are deducted from revenue.", "Revenue − total costs"),
            ("Profit margin", "The percentage of revenue remaining as operating profit.", "Operating profit ÷ revenue × 100"),
            ("Contribution margin per unit", "The amount each unit contributes toward fixed costs and profit.", "Selling price per unit − variable cost per unit"),
            ("Break-even volume", "The number of units that must be sold for estimated revenue to cover the modeled costs.", "(Fixed costs + marketing spend) ÷ contribution margin per unit"),
        ),
    ),
    (
        "SCENARIO TERMS",
        (
            ("Current scenario", "The business’s original financial position before slider adjustments are applied.", None),
            ("Proposed scenario", "The estimated financial position after the selected changes are applied.", None),
            ("Selling-price change", "The percentage increase or decrease applied to the selling price per unit.", None),
            ("Sales-volume change", "The percentage increase or decrease applied to expected unit sales, independent of any price change.", None),
            ("Price elasticity of demand", "How strongly customers react to a price change. At -1.5, a 1% price rise loses about 1.5% of volume. At 0 (off), volume ignores price.", "Proposed units = units × (1 + volume change) × (1 + price change) ^ elasticity"),
            ("Most profitable price change", "With elasticity set, the price change between -20% and +20% that gives the highest operating profit, holding every other assumption.", None),
            ("Unit-cost change", "The percentage increase or decrease applied to variable cost per unit.", None),
            ("Fixed-cost change", "The percentage increase or decrease applied to fixed operating costs.", None),
            ("Marketing-spend change", "The percentage increase or decrease applied to the marketing budget.", None),
            ("Assumption", "A value selected by the user for scenario analysis. It is not a guaranteed forecast.", None),
            ("Percentage points (pp)", "The difference between two percentages. A margin moving from 21.3% to 18.4% falls 2.9 pp, not 2.9%.", "Proposed margin − current margin"),
        ),
    ),
    (
        "RISK ANALYSIS",
        (
            ("Monte Carlo simulation", "A technique that runs many possible outcomes using uncertainty ranges selected by the user.", None),
            ("Probability of improvement", "The percentage of simulations in which proposed operating profit exceeds current operating profit.", None),
            ("Probability of loss", "The percentage of simulations that produce negative operating profit.", None),
            ("10th percentile", "A conservative result. Approximately 10% of simulated outcomes are below this value.", None),
            ("Median", "The middle simulated result.", None),
            ("90th percentile", "An optimistic result. Approximately 90% of simulated outcomes are below this value.", None),
        ),
    ),
)


class BusinessGlossaryDialog(QDialog):
    """Theme-aware reference dialog for the application's business terms."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("MarginPilot Business Glossary")
        self.setModal(True)
        self.setMinimumSize(560, 500)
        self.resize(720, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("MarginPilot Business Glossary")
        title.setObjectName("glossaryTitle")
        introduction = QLabel(
            "Plain-language definitions for the operating inputs, financial results, "
            "scenario controls, and risk measures used in MarginPilot."
        )
        introduction.setObjectName("mutedLabel")
        introduction.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(introduction)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 4, 12, 12)
        content_layout.setSpacing(6)

        for section_name, entries in SECTIONS:
            section = QLabel(section_name)
            section.setObjectName("glossarySection")
            content_layout.addWidget(section)
            for term, definition, formula in entries:
                term_label = QLabel(term)
                term_label.setObjectName("glossaryTerm")
                definition_label = QLabel(definition)
                definition_label.setObjectName("glossaryDefinition")
                definition_label.setWordWrap(True)
                definition_label.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                )
                content_layout.addWidget(term_label)
                content_layout.addWidget(definition_label)
                if formula:
                    formula_label = QLabel(f"Formula:  {formula}")
                    formula_label.setObjectName("formulaBox")
                    formula_label.setWordWrap(True)
                    formula_label.setTextInteractionFlags(
                        Qt.TextInteractionFlag.TextSelectableByMouse
                    )
                    content_layout.addWidget(formula_label)

        disclaimer = QLabel(
            "MarginPilot provides scenario-based estimates using values supplied by "
            "the user. Its results are decision-support information, not guaranteed "
            "financial forecasts."
        )
        disclaimer.setObjectName("disclaimerBox")
        disclaimer.setWordWrap(True)
        disclaimer.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_layout.addSpacing(8)
        content_layout.addWidget(disclaimer)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        root.addWidget(buttons)
