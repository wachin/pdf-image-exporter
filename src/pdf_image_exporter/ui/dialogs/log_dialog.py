"""In-application log viewer."""

from __future__ import annotations

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...metadata import APP_NAME
from ...services.logging_service import QtLogHandler


class LogDialog(QDialog):
    """A simple read-only log viewer."""

    def __init__(self, handler: QtLogHandler, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("{app} Log").format(app=APP_NAME))
        self.resize(760, 460)
        self._handler = handler
        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setPlainText("\n".join(handler.records()))
        layout.addWidget(self.editor)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        copy_button = QPushButton(self.tr("Copy"))
        buttons.addButton(copy_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)
        copy_button.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(buttons)
        handler.messageLogged.connect(self.append_message)

    def append_message(self, message: str) -> None:
        self.editor.appendPlainText(message)

    def copy_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self.editor.toPlainText())
