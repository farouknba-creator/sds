"""
Review tab - Phase 1 stub.

Phase 6 will replace this with side-by-side original vs. generated viewer
plus approve / edit / reject workflow.
"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ReviewTab(QWidget):
    def __init__(self, status_cb=None):
        super().__init__()
        self.status_cb = status_cb or (lambda msg: None)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "<h2>Review Queue</h2>"
            "<p>Available in Phase 6.</p>"
            "<p>Items flagged during processing will appear here for human review.</p>"
        ))
        v.addStretch()
