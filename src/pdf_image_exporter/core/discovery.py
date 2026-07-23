"""PDF file discovery helpers."""

from __future__ import annotations

from pathlib import Path


def discover_pdf_files(directory: Path, recursive: bool = False) -> list[Path]:
    """Return PDF files in deterministic order from a directory."""

    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    pattern = "**/*" if recursive else "*"
    paths = [
        path
        for path in directory.glob(pattern)
        if path.is_file() and path.suffix.lower() == ".pdf"
    ]
    return sorted(paths, key=lambda path: path.as_posix().casefold())
