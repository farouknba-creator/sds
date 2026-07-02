"""
SDS Studio - application entry point.

Run in dev:  python -m sds_studio.main
Packaged:    double-click SDSStudio.exe
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SDS Studio")
    app.setOrganizationName("SDS Studio")
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
