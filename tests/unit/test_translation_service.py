from __future__ import annotations

from pdf_image_exporter.services.translation_service import (
    effective_language_code,
    normalized_language_code,
)


def test_normalized_language_code() -> None:
    assert normalized_language_code("es") == "es"
    assert normalized_language_code("unknown") == "system"


def test_effective_language_code_for_explicit_language() -> None:
    assert effective_language_code("en") == "en"
    assert effective_language_code("es") == "es"
