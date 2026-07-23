"""Conversion configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .formats import FormatOptions, OutputFormat


@dataclass(frozen=True)
class ConversionSettings:
    """Settings shared by GUI and CLI conversions."""

    output_format: OutputFormat = OutputFormat.PNG
    dpi: int = 150
    page_expression: str = "all"
    output_dir: Path | None = None
    name_template: str = "{document}-{page}"
    page_digits: int = 3
    format_options: FormatOptions = FormatOptions()

    def validate(self) -> None:
        if self.dpi < 1 or self.dpi > 2400:
            raise ValueError("DPI must be between 1 and 2400.")
        if self.page_digits < 1 or self.page_digits > 12:
            raise ValueError("Page digits must be between 1 and 12.")
