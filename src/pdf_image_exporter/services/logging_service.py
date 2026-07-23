"""Application logging setup."""

from __future__ import annotations

import logging
from collections import deque
from pathlib import Path

from PyQt6.QtCore import QObject, QStandardPaths, pyqtSignal

from ..metadata import APP_ID


class QtLogHandler(QObject, logging.Handler):
    """A logging handler that emits sanitized log records to Qt widgets."""

    messageLogged = pyqtSignal(str)

    def __init__(self, capacity: int = 500) -> None:
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self._records: deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self._records.append(message)
        self.messageLogged.emit(message)

    def records(self) -> list[str]:
        return list(self._records)


def log_dir() -> Path:
    """Return the XDG-compatible application log directory."""

    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.GenericDataLocation
    )
    if not base:
        base = str(Path.home() / ".local" / "share")
    return Path(base) / APP_ID / "logs"


def configure_logging(level: int = logging.INFO) -> QtLogHandler:
    """Configure file and in-memory logging for the application."""

    directory = log_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        directory = Path("/tmp") / APP_ID / "logs"
        directory.mkdir(parents=True, exist_ok=True)
    log_file = directory / "pdf-image-exporter.log"
    logger = logging.getLogger("pdf_image_exporter")
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    qt_handler = QtLogHandler()
    qt_handler.setFormatter(formatter)
    qt_handler.setLevel(level)
    logger.addHandler(qt_handler)
    return qt_handler
