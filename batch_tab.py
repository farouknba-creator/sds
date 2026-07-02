"""
Batch tab - Phase 1 stub.

Phase 5 will replace this with:
  - drag-drop zone
  - supplier dropdown
  - standard dropdown
  - progress bar + live log
  - per-file status table
"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class BatchTab(QWidget):
    def __init__(self, db, template_config, status_cb=None):
        super().__init__()
        self.db = db
        self.template_config = template_config
        self.status_cb = status_cb or (lambda msg: None)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "<h2>Batch Processor</h2>"
            "<p>Available in Phase 5.</p>"
            "<p>Will support: drag-drop PDF input, supplier & standard selection, "
            "live progress, per-file status, output to <code>output/</code>.</p>"
        ))
        v.addStretch()
