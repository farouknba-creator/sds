"""
SDS Studio - main window.

Holds the 5-tab layout. Phase 1 ships with Suppliers + Settings fully
functional; Batch / Template / Review are stubs that get built out later.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.paths import ensure_dirs
from ..core.supplier import SupplierDB
from ..core.template_config import TemplateConfig
from .batch_tab import BatchTab
from .review_tab import ReviewTab
from .settings_tab import SettingsTab
from .suppliers_tab import SuppliersTab
from .template_tab import TemplateTab


APP_TITLE = "SDS Studio"
APP_VERSION = "0.1.0"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.db = SupplierDB()
        self.template_config = TemplateConfig()

        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.resize(1400, 900)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QLabel(f"<h3>{APP_TITLE}</h3>"
                        f"<span style='color:#666'>SDS batch reformatting • portable • v{APP_VERSION}</span>")
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_batch = BatchTab(self.db, self.template_config, self._status)
        self.tab_suppliers = SuppliersTab(self.db, self._status)
        self.tab_template = TemplateTab(self.template_config, self._status)
        self.tab_review = ReviewTab(self._status)
        self.tab_settings = SettingsTab(self._status)

        self.tabs.addTab(self.tab_batch, "1. Batch")
        self.tabs.addTab(self.tab_suppliers, "2. Suppliers")
        self.tabs.addTab(self.tab_template, "3. Template")
        self.tabs.addTab(self.tab_review, "4. Review")
        self.tabs.addTab(self.tab_settings, "5. Settings")
        layout.addWidget(self.tabs, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self._status("Ready. Configure AI provider in Settings, suppliers in Suppliers tab.")

    def _status(self, msg: str) -> None:
        self.statusBar().showMessage(msg, 8000)
