from __future__ import annotations

import logging

from pdf_image_exporter.services.logging_service import QtLogHandler


def test_qt_log_handler_keeps_recent_records() -> None:
    handler = QtLogHandler(capacity=2)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    logger = logging.getLogger("pdf_image_exporter.tests.handler")
    logger.handlers.clear()
    logger.propagate = False
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("one")
    logger.warning("two")
    logger.error("three")

    assert handler.records() == ["WARNING:two", "ERROR:three"]
