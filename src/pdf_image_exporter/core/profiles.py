"""Conversion profiles."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .conversion import ConversionSettings
from .formats import FormatOptions, OutputFormat

PROFILE_ID_RE = re.compile(r"[^a-z0-9-]+")


@dataclass(frozen=True)
class ConversionProfile:
    """A named set of conversion defaults."""

    identifier: str
    name: str
    description: str
    settings: ConversionSettings
    built_in: bool = True

    def to_dict(self) -> dict[str, Any]:
        options = self.settings.format_options
        return {
            "identifier": self.identifier,
            "name": self.name,
            "description": self.description,
            "built_in": self.built_in,
            "settings": {
                "format": self.settings.output_format.value,
                "dpi": self.settings.dpi,
                "page_expression": self.settings.page_expression,
                "name_template": self.settings.name_template,
                "page_digits": self.settings.page_digits,
                "format_options": {
                    "jpeg_quality": options.jpeg_quality,
                    "jpeg_progressive": options.jpeg_progressive,
                    "tiff_compression": options.tiff_compression,
                    "transparent_background": options.transparent_background,
                    "grayscale": options.grayscale,
                    "monochrome": options.monochrome,
                },
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversionProfile":
        settings_data = data["settings"]
        output_format = OutputFormat(settings_data["format"])
        options_data = settings_data.get("format_options", {})
        return cls(
            identifier=str(data["identifier"]),
            name=str(data["name"]),
            description=str(data.get("description", "")),
            built_in=bool(data.get("built_in", False)),
            settings=ConversionSettings(
                output_format=output_format,
                dpi=int(settings_data.get("dpi", 150)),
                page_expression=str(settings_data.get("page_expression", "all")),
                name_template=str(
                    settings_data.get("name_template", "{document}-{page}")
                ),
                page_digits=int(settings_data.get("page_digits", 3)),
                format_options=FormatOptions(
                    output_format=output_format,
                    jpeg_quality=int(options_data.get("jpeg_quality", 90)),
                    jpeg_progressive=bool(options_data.get("jpeg_progressive", False)),
                    tiff_compression=str(
                        options_data.get("tiff_compression", "deflate")
                    ),
                    transparent_background=bool(
                        options_data.get("transparent_background", False)
                    ),
                    grayscale=bool(options_data.get("grayscale", False)),
                    monochrome=bool(options_data.get("monochrome", False)),
                ),
            ),
        )


def default_profiles() -> tuple[ConversionProfile, ...]:
    """Return the built-in profiles required by the product roadmap."""

    return (
        _profile(
            "screen-messaging", "Screen and messaging", OutputFormat.JPEG, 150, 82
        ),
        _profile("web-standard", "Web standard", OutputFormat.JPEG, 150, 88),
        _profile("web-high-quality", "Web high quality", OutputFormat.PNG, 200, 90),
        _profile("social-media", "Social media", OutputFormat.JPEG, 150, 85),
        _profile("screen-reading", "Screen reading", OutputFormat.PNG, 150, 90),
        _profile("print-standard", "Standard print", OutputFormat.PNG, 300, 90),
        _profile("print-high-quality", "High quality print", OutputFormat.PNG, 600, 90),
        _profile("lossless-archive", "Lossless archive", OutputFormat.PNG, 300, 90),
        _profile("light-jpeg", "Light JPEG", OutputFormat.JPEG, 96, 70),
        _profile("thumbnails", "Thumbnails", OutputFormat.JPEG, 72, 75),
        _profile("ocr-processing", "OCR or post-processing", OutputFormat.PNG, 300, 90),
    )


def export_profiles(path: Path, profiles: list[ConversionProfile]) -> None:
    """Write profiles as UTF-8 JSON."""

    payload = [profile.to_dict() for profile in profiles]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "utf-8")


def import_profiles(path: Path) -> list[ConversionProfile]:
    """Read profiles from UTF-8 JSON."""

    data = json.loads(path.read_text("utf-8"))
    if not isinstance(data, list):
        raise ValueError("Profile file must contain a list.")
    return [ConversionProfile.from_dict(item) for item in data]


def profile_identifier_from_name(name: str) -> str:
    """Create a stable user-profile identifier from a display name."""

    identifier = PROFILE_ID_RE.sub("-", name.strip().lower()).strip("-")
    return f"user-{identifier or 'profile'}"


def _profile(
    identifier: str,
    name: str,
    output_format: OutputFormat,
    dpi: int,
    jpeg_quality: int,
) -> ConversionProfile:
    return ConversionProfile(
        identifier=identifier,
        name=name,
        description=name,
        settings=ConversionSettings(
            output_format=output_format,
            dpi=dpi,
            format_options=FormatOptions(
                output_format=output_format,
                jpeg_quality=jpeg_quality,
            ),
        ),
        built_in=True,
    )
