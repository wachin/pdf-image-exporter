from __future__ import annotations

from pdf_image_exporter.core.dimensions import PageSize, recognize_standard_size


def test_a4_recognition_and_pixels() -> None:
    size = PageSize(595, 842)
    assert recognize_standard_size(size) == "A4"
    assert size.orientation == "portrait"
    assert size.pixels_at(300) == (2479, 3508)


def test_landscape_letter_recognition() -> None:
    size = PageSize(792, 612)
    assert recognize_standard_size(size) == "Letter"
    assert size.orientation == "landscape"
