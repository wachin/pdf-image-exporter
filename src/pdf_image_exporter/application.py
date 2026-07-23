"""Qt application bootstrap."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget

from .metadata import APP_ID, APP_NAME, VERSION
from .services.logging_service import configure_logging
from .services.process_service import find_executable
from .ui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    """Start the graphical application."""

    args = sys.argv if argv is None else argv
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(VERSION)
    QCoreApplication.setOrganizationName("PDF Image Exporter")
    QCoreApplication.setOrganizationDomain("example.invalid")

    app = QApplication(args)
    app.setDesktopFileName(APP_ID)
    log_handler = configure_logging()

    if find_executable("pdftocairo") is None or find_executable("pdfinfo") is None:
        QMessageBox.critical(
            QWidget(),
            APP_NAME,
            "Poppler tools were not found. Please install them with:\n\n"
            "sudo apt install poppler-utils",
        )
        return 1

    window = MainWindow(log_handler=log_handler)
    window.show()
    return app.exec()
