"""Output format definitions and Poppler capability mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OutputFormat(str, Enum):
    """Image formats supported by the first implementation."""

    PNG = "png"
    JPEG = "jpeg"
    TIFF = "tiff"

    @property
    def extension(self) -> str:
        if self is OutputFormat.JPEG:
            return "jpg"
        return str(self.value)

    @property
    def pdftocairo_flag(self) -> str:
        return f"-{self.value}"


@dataclass(frozen=True)
class FormatOptions:
    """Format-specific options supported by current Poppler capabilities."""

    output_format: OutputFormat = OutputFormat.PNG
    jpeg_quality: int = 90
    jpeg_progressive: bool = False
    tiff_compression: str = "deflate"
    transparent_background: bool = False
    grayscale: bool = False
    monochrome: bool = False


@dataclass(frozen=True)
class PopplerCapabilities:
    """Detected command-line capabilities from `pdftocairo -h`."""

    version: str
    supported_formats: frozenset[OutputFormat]
    tiff_compressions: frozenset[str] = field(default_factory=frozenset)
    supports_jpegopt: bool = False
    supports_transparency: bool = False
    supports_antialias: bool = False
    supports_icc: bool = False

    @classmethod
    def from_help(cls, version: str, help_text: str) -> "PopplerCapabilities":
        formats: set[OutputFormat] = set()
        if "-png" in help_text:
            formats.add(OutputFormat.PNG)
        if "-jpeg" in help_text:
            formats.add(OutputFormat.JPEG)
        if "-tiff" in help_text:
            formats.add(OutputFormat.TIFF)
        compressions = {"none", "packbits", "jpeg", "lzw", "deflate"}
        return cls(
            version=version,
            supported_formats=frozenset(formats),
            tiff_compressions=frozenset(compressions)
            if "-tiffcompression" in help_text
            else frozenset(),
            supports_jpegopt="-jpegopt" in help_text,
            supports_transparency="-transp" in help_text,
            supports_antialias="-antialias" in help_text,
            supports_icc="-icc" in help_text,
        )
