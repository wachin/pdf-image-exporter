from __future__ import annotations

from pathlib import Path

from pdf_image_exporter.core.conversion import ConversionSettings
from pdf_image_exporter.core.formats import OutputFormat
from pdf_image_exporter.core.profiles import (
    ConversionProfile,
    profile_identifier_from_name,
)
from pdf_image_exporter.services.profile_store import ProfileStore


def test_profile_identifier_from_name() -> None:
    assert profile_identifier_from_name("My Print Profile!") == "user-my-print-profile"


def test_profile_store_add_replace_delete_and_restore(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path / "profiles.json")
    profile = ConversionProfile(
        identifier="user-test",
        name="Test",
        description="Test",
        settings=ConversionSettings(output_format=OutputFormat.PNG, dpi=300),
        built_in=False,
    )

    store.add_or_replace_user_profile(profile)
    assert store.user_profiles() == [profile]
    assert any(item.identifier == "print-standard" for item in store.all_profiles())

    replacement = ConversionProfile(
        identifier="user-test",
        name="Test replacement",
        description="Test replacement",
        settings=ConversionSettings(output_format=OutputFormat.JPEG, dpi=96),
        built_in=False,
    )
    store.add_or_replace_user_profile(replacement)
    loaded = store.user_profiles()
    assert len(loaded) == 1
    assert loaded[0].identifier == replacement.identifier
    assert loaded[0].name == replacement.name
    assert loaded[0].settings.output_format is OutputFormat.JPEG
    assert loaded[0].settings.dpi == 96

    assert store.delete_user_profile("user-test")
    assert not store.user_profiles()

    store.add_or_replace_user_profile(profile)
    store.restore_defaults()
    assert not store.user_profiles()
