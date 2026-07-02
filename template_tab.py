"""
Template tab - Phase 1 stub.

Phase 6 will replace this with template preview and per-standard section
reordering UI.
"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class TemplateTab(QWidget):
    def __init__(self, template_config, status_cb=None):
        super().__init__()
        self.template_config = template_config
        self.status_cb = status_cb or (lambda msg: None)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "<h2>Template Designer</h2>"
            "<p>Available in Phase 6.</p>"
            "<p>Config is loaded from <code>config/template_config.yaml</code> - "
            "edit that file directly for now.</p>"
        ))
        codes = ", ".join(template_config.standards_codes())
        v.addWidget(QLabel(f"<p>Available standards: <b>{codes}</b></p>"))
        v.addStretch()
