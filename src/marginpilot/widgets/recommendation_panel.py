"""Management assessment presentation panel."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from marginpilot.models.recommendation_model import ManagementAssessment


class RecommendationPanel(QFrame):
    """Renders a rule-based interpretation of the current scenario."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("recommendationPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(5)
        heading_row = QHBoxLayout()
        title = QLabel("Management Assessment")
        title.setObjectName("sectionTitle")
        self.status_badge = QLabel("Neutral or Inconclusive")
        self.status_badge.setObjectName("assessmentBadge")
        heading_row.addWidget(title)
        heading_row.addStretch()
        heading_row.addWidget(self.status_badge)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setObjectName("recommendationText")
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName("assumptionsNote")
        layout.addLayout(heading_row)
        layout.addWidget(self.summary)
        layout.addWidget(self.note)

    def show_assessment(self, assessment: ManagementAssessment) -> None:
        self.summary.setText(assessment.summary)
        self.note.setText(assessment.assumptions_note)
        self.status_badge.setText(assessment.status)
        self.setProperty("assessmentTone", assessment.tone)
        self.status_badge.setProperty("assessmentTone", assessment.tone)
        for widget in (self, self.status_badge):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
