from __future__ import annotations

from pathlib import Path

import pytest

from pdf_image_exporter.core.discovery import discover_pdf_files


def test_discover_pdf_files_non_recursive(tmp_path: Path) -> None:
    (tmp_path / "b.PDF").write_text("pdf", "utf-8")
    (tmp_path / "a.pdf").write_text("pdf", "utf-8")
    (tmp_path / "note.txt").write_text("text", "utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "c.pdf").write_text("pdf", "utf-8")

    assert discover_pdf_files(tmp_path) == [tmp_path / "a.pdf", tmp_path / "b.PDF"]


def test_discover_pdf_files_recursive(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "a.pdf").write_text("pdf", "utf-8")
    (nested / "b.pdf").write_text("pdf", "utf-8")

    assert discover_pdf_files(tmp_path, recursive=True) == [
        tmp_path / "a.pdf",
        nested / "b.pdf",
    ]


def test_discover_pdf_files_rejects_non_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "file.pdf"
    file_path.write_text("pdf", "utf-8")

    with pytest.raises(NotADirectoryError):
        discover_pdf_files(file_path)
