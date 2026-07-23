from __future__ import annotations

from pathlib import Path

from pdf_image_exporter.core.formats import OutputFormat
from pdf_image_exporter.core.profiles import (
    default_profiles,
    export_profiles,
    import_profiles,
)


def test_default_profiles_cover_required_set() -> None:
    identifiers = {profile.identifier for profile in default_profiles()}
    assert {
        "screen-messaging",
        "web-standard",
        "web-high-quality",
        "social-media",
        "screen-reading",
        "print-standard",
        "print-high-quality",
        "lossless-archive",
        "light-jpeg",
        "thumbnails",
        "ocr-processing",
    } <= identifiers


def test_profile_json_round_trip(tmp_path: Path) -> None:
    source = [default_profiles()[0]]
    path = tmp_path / "profiles.json"
    export_profiles(path, source)
    loaded = import_profiles(path)
    assert loaded[0].identifier == source[0].identifier
    assert loaded[0].settings.output_format is OutputFormat.JPEG
