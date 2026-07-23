"""Qt application bootstrap."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget

from .metadata import APP_ID, APP_NAME, VERSION
from .services.process_service import find_executable
from .ui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    """Start the graphical application."""

    args = sys.argv if argv is None else argv
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(VERSION)
    QCoreApplication.setOrganizationName("PDF Image Exporter")
    QCoreApplication.setApplicationName(APP_NAME)

    app = QApplication(args)
    app.setDesktopFileName(APP_ID)

    if find_executable("pdftocairo") is None or find_executable("pdfinfo") is None:
        QMessageBox.critical(
            QWidget(),
            APP_NAME,
            "Poppler tools were not found. Please install them with:\n\n"
            "sudo apt install poppler-utils",
        )
        return 1

    window = MainWindow()
    window.show()
    return app.exec()
