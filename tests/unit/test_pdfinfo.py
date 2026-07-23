from __future__ import annotations

from pathlib import Path

from pdf_image_exporter.core.pdf_info import parse_pdfinfo_output


def test_parse_pdfinfo_with_page_boxes() -> None:
    output = """Title:           Example
Pages:           2
Encrypted:       no
Page    1 size:  595 x 842 pts (A4)
Page    2 size:  842 x 595 pts (A4)
"""
    info = parse_pdfinfo_output(Path("example.pdf"), output)
    assert info.pages == 2
    assert info.title == "Example"
    assert info.primary_page_size is not None
    assert info.has_mixed_page_sizes
    assert info.page_size(2) is not None
    assert info.display_page_size(2).startswith("A4,")


def test_parse_pdfinfo_single_size_falls_back_for_page() -> None:
    output = """Pages:           3
Page size:       595 x 842 pts (A4)
"""
    info = parse_pdfinfo_output(Path("example.pdf"), output)
    assert info.page_size(3) == info.primary_page_size
    assert not info.has_mixed_page_sizes
