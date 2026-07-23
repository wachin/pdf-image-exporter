from __future__ import annotations

from pdf_image_exporter.core.errors import user_error_message


def test_user_error_message_for_collision() -> None:
    assert "already exists" in user_error_message(FileExistsError("x"))


def test_user_error_message_for_validation() -> None:
    assert user_error_message(ValueError("Bad page range")) == "Bad page range"
