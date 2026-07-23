"""PDF metadata models and parsers for `pdfinfo` output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .dimensions import PageSize, recognize_standard_size

PAGE_SIZE_RE = re.compile(
    r"Page(?:\s+\d+)?\s+size:\s+" r"(?P<width>[0-9.]+)\s+x\s+(?P<height>[0-9.]+)\s+pts"
)


@dataclass(frozen=True)
class PdfDocumentInfo:
    """Subset of PDF metadata needed by the initial UI."""

    path: Path
    pages: int
    page_sizes: tuple[PageSize, ...]
    title: str = ""
    author: str = ""
    encrypted: bool = False
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def primary_page_size(self) -> PageSize | None:
        return self.page_sizes[0] if self.page_sizes else None

    @property
    def has_mixed_page_sizes(self) -> bool:
        if not self.page_sizes:
            return False
        first = self.page_sizes[0]
        return any(
            abs(size.width_points - first.width_points) > 0.5
            or abs(size.height_points - first.height_points) > 0.5
            for size in self.page_sizes[1:]
        )

    def display_size_summary(self) -> str:
        size = self.primary_page_size
        if size is None:
            return "Unknown"
        name = recognize_standard_size(size)
        suffix = " mixed" if self.has_mixed_page_sizes else ""
        return (
            f"{name} {size.width_mm:.0f} x {size.height_mm:.0f} mm, "
            f"{size.width_points:.0f} x {size.height_points:.0f} pt{suffix}"
        )


def parse_pdfinfo_output(path: Path, output: str) -> PdfDocumentInfo:
    """Parse the stable parts of `pdfinfo` text output."""

    raw: dict[str, str] = {}
    pages = 0
    title = ""
    author = ""
    encrypted = False
    page_sizes: list[PageSize] = []

    for line in output.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            raw[key.strip()] = value.strip()

        stripped = line.strip()
        if stripped.startswith("Pages:"):
            pages = int(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("Title:"):
            title = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Author:"):
            author = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Encrypted:"):
            encrypted = stripped.split(":", 1)[1].strip().lower().startswith("yes")

        match = PAGE_SIZE_RE.match(stripped)
        if match:
            page_sizes.append(
                PageSize(
                    width_points=float(match.group("width")),
                    height_points=float(match.group("height")),
                )
            )

    return PdfDocumentInfo(
        path=path,
        pages=pages,
        page_sizes=tuple(page_sizes),
        title=title,
        author=author,
        encrypted=encrypted,
        raw=raw,
    )
