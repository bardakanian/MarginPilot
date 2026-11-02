"""Executive-summary exports: scenario data as CSV and a printable PDF."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QMarginsF, QSizeF, QUrl
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from marginpilot.models.financial_model import (
    FinancialInputs,
    FinancialResults,
    ScenarioChanges,
    percentage_change,
)
from marginpilot.models.recommendation_model import ManagementAssessment

# Two charts side by side across the printable width, in document pixels.
CHART_WIDTH = 335

DISCLAIMER = (
    "Scenario-based estimates using values supplied by the user. Decision-support "
    "information, not a guaranteed financial forecast."
)


@dataclass(frozen=True, slots=True)
class ScenarioSnapshot:
    """Everything needed to reproduce one dashboard state outside the app."""

    baseline: FinancialInputs
    proposed_inputs: FinancialInputs
    changes: ScenarioChanges
    current: FinancialResults
    proposed: FinancialResults
    assessment: ManagementAssessment
    source_name: str | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now().replace(microsecond=0))


@dataclass(frozen=True, slots=True)
class ReportRow:
    """One current-versus-proposed line of the summary."""

    section: str
    item: str
    current: float | None
    proposed: float | None
    unit: str

    @property
    def change(self) -> float | None:
        if self.current is None or self.proposed is None:
            return None
        return self.proposed - self.current

    @property
    def change_pct(self) -> float | None:
        # A change in a percentage is reported in points, not as a relative change.
        if self.unit == "%":
            return None
        return percentage_change(self.current, self.proposed)


def report_rows(snapshot: ScenarioSnapshot) -> list[ReportRow]:
    """Results first, then the assumptions that produced them."""

    current, proposed = snapshot.current, snapshot.proposed
    base, plan = snapshot.baseline, snapshot.proposed_inputs
    return [
        ReportRow("Results", "Revenue", current.revenue, proposed.revenue, "$"),
        ReportRow("Results", "Total costs", current.total_costs, proposed.total_costs, "$"),
        ReportRow(
            "Results",
            "Operating profit",
            current.operating_profit,
            proposed.operating_profit,
            "$",
        ),
        ReportRow("Results", "Profit margin", current.profit_margin, proposed.profit_margin, "%"),
        ReportRow(
            "Results",
            "Contribution margin / unit",
            current.contribution_margin_per_unit,
            proposed.contribution_margin_per_unit,
            "$/unit",
        ),
        ReportRow(
            "Results",
            "Break-even units",
            current.break_even_units,
            proposed.break_even_units,
            "units",
        ),
        ReportRow("Assumptions", "Units sold", base.units_sold, plan.units_sold, "units"),
        ReportRow(
            "Assumptions",
            "Selling price / unit",
            base.price_per_unit,
            plan.price_per_unit,
            "$/unit",
        ),
        ReportRow(
            "Assumptions",
            "Variable cost / unit",
            base.variable_cost_per_unit,
            plan.variable_cost_per_unit,
            "$/unit",
        ),
        ReportRow("Assumptions", "Fixed costs", base.fixed_costs, plan.fixed_costs, "$"),
        ReportRow(
            "Assumptions", "Marketing spend", base.marketing_spend, plan.marketing_spend, "$"
        ),
    ]


def scenario_levers(changes: ScenarioChanges) -> list[tuple[str, str]]:
    """Human-readable scenario settings, including the elasticity assumption."""

    elasticity = (
        "Off (volume ignores price)"
        if changes.price_elasticity == 0
        else f"{changes.price_elasticity:.1f}"
    )
    return [
        ("Selling price change", f"{changes.price:+.1f}%"),
        ("Sales volume change", f"{changes.volume:+.1f}%"),
        ("Price elasticity of demand", elasticity),
        ("Unit cost change", f"{changes.variable_cost:+.1f}%"),
        ("Fixed cost change", f"{changes.fixed_cost:+.1f}%"),
        ("Marketing spend change", f"{changes.marketing:+.1f}%"),
    ]


def write_scenario_csv(snapshot: ScenarioSnapshot, path: str | Path) -> Path:
    """Write unrounded scenario figures for further analysis in a spreadsheet."""

    target = Path(path)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "item", "unit", "current", "proposed", "change", "change_pct"])
        for row in report_rows(snapshot):
            writer.writerow(
                [
                    row.section,
                    row.item,
                    row.unit,
                    _raw(row.current),
                    _raw(row.proposed),
                    _raw(row.change),
                    _raw(row.change_pct),
                ]
            )
        for name, value in scenario_levers(snapshot.changes):
            writer.writerow(["Scenario", name, "", "", value, "", ""])
        writer.writerow(["Assessment", "Status", "", "", snapshot.assessment.status, "", ""])
        writer.writerow(["Assessment", "Summary", "", "", snapshot.assessment.summary, "", ""])
    return target


def build_report_html(
    snapshot: ScenarioSnapshot, chart_urls: dict[str, str] | None = None
) -> str:
    """Return the executive summary as HTML that QTextDocument can paginate."""

    charts = chart_urls or {}
    source = escape(snapshot.source_name) if snapshot.source_name else "Manual entry"
    tone_color = {"positive": "#08756A", "negative": "#B42318"}.get(
        snapshot.assessment.tone, "#475467"
    )
    rows_html = []
    current_section = ""
    for row in report_rows(snapshot):
        if row.section != current_section:
            current_section = row.section
            rows_html.append(
                f'<tr><td colspan="4" class="section">{escape(row.section)}</td></tr>'
            )
        rows_html.append(
            "<tr>"
            f"<td>{escape(row.item)}</td>"
            f'<td align="right">{format_value(row.current, row.unit)}</td>'
            f'<td align="right">{format_value(row.proposed, row.unit)}</td>'
            f'<td align="right">{format_change(row)}</td>'
            "</tr>"
        )
    levers_html = "".join(
        f"<tr><td>{escape(name)}</td><td align=\"right\">{escape(value)}</td></tr>"
        for name, value in scenario_levers(snapshot.changes)
    )
    chart_cells = "".join(
        f'<td class="chart"><img src="{escape(url)}" width="{CHART_WIDTH}"></td>'
        for url in (charts.get("comparison"), charts.get("sensitivity"))
        if url
    )
    chart_html = f'<table cellspacing="0"><tr>{chart_cells}</tr></table>' if chart_cells else ""
    return f"""
<html><head><style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #172033; font-size: 8.5pt; }}
  h1 {{ font-size: 16pt; margin: 0; }}
  h2 {{ font-size: 10.5pt; margin-top: 12px; margin-bottom: 4px; }}
  .meta {{ color: #5F6B7A; }}
  .status {{ color: {tone_color}; font-weight: bold; }}
  table {{ border-collapse: collapse; }}
  th {{ background: #E8EEF5; text-align: left; padding: 4px 8px; }}
  td {{ padding: 3px 8px; border-bottom: 1px solid #DCE3EC; }}
  td.chart {{ border: none; padding: 0 6px 0 0; }}
  td.section {{ font-weight: bold; background: #F4F7FB; }}
  .disclaimer {{ color: #5F6B7A; font-size: 8pt; }}
</style></head><body>
<h1>MarginPilot Executive Summary</h1>
<p class="meta">Generated {snapshot.generated_at:%Y-%m-%d %H:%M}
  &nbsp;•&nbsp; Baseline: {source}</p>
<h2>Management assessment
  &nbsp;<span class="status">{escape(snapshot.assessment.status)}</span></h2>
<p>{escape(snapshot.assessment.summary)}</p>
<p class="meta">{escape(snapshot.assessment.assumptions_note)}</p>
{chart_html}
<h2>Current vs. proposed</h2>
<table width="100%" cellspacing="0">
<tr><th>Measure</th><th align="right">Current</th>
  <th align="right">Proposed</th><th align="right">Change</th></tr>
{''.join(rows_html)}
</table>
<h2>Scenario settings</h2>
<table width="60%" cellspacing="0">{levers_html}</table>
<p class="disclaimer">{DISCLAIMER}
  Prepared locally with MarginPilot; no data left this computer.</p>
</body></html>
"""


def write_pdf_report(
    snapshot: ScenarioSnapshot,
    path: str | Path,
    chart_images: dict[str, QImage] | None = None,
) -> Path:
    """Render the executive summary to an A4 PDF."""

    target = Path(path)
    document = QTextDocument()
    urls: dict[str, str] = {}
    for name, image in (chart_images or {}).items():
        url = f"chart://{name}"
        document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(url), image)
        urls[name] = url
    document.setHtml(build_report_html(snapshot, urls))

    writer = QPdfWriter(str(target))
    writer.setTitle("MarginPilot Executive Summary")
    writer.setCreator("MarginPilot")
    writer.setPageLayout(
        QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(14, 14, 14, 14),
            QPageLayout.Unit.Millimeter,
        )
    )
    # Lay the document out on the printable area itself; otherwise print_()
    # adds its own 2 cm margin inside the page margins.
    writer.setResolution(96)
    printable = writer.pageLayout().paintRectPixels(writer.resolution()).size()
    document.setDocumentMargin(0)
    document.setPageSize(QSizeF(printable))
    document.print_(writer)
    if not target.exists() or target.stat().st_size == 0:
        raise OSError(f"The PDF could not be written: {target}")
    return target


def format_value(value: float | None, unit: str) -> str:
    if value is None:
        return "N/A"
    if unit == "%":
        return f"{value:,.1f}%"
    if unit == "units":
        return f"{value:,.0f}"
    sign = "-" if value < 0 else ""
    decimals = 2 if unit == "$/unit" else 0
    return f"{sign}${abs(value):,.{decimals}f}"


def format_change(row: ReportRow) -> str:
    change = row.change
    if change is None:
        return "N/A"
    if row.unit == "%":
        return f"{change:+.1f} pp"
    sign = "+" if change >= 0 else "-"
    magnitude = format_value(abs(change), row.unit)
    pct = row.change_pct
    return f"{sign}{magnitude}" + (f" ({pct:+.1f}%)" if pct is not None else "")


def _raw(value: float | None) -> str:
    return "" if value is None else repr(round(value, 6))
