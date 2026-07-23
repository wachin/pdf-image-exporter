"""XDG-backed user profile storage."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QStandardPaths

from ..core.profiles import (
    ConversionProfile,
    default_profiles,
    export_profiles,
    import_profiles,
)
from ..metadata import APP_ID


def profile_config_dir() -> Path:
    """Return the XDG-compatible profile configuration directory."""

    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.GenericConfigLocation
    )
    if not base:
        base = str(Path.home() / ".config")
    return Path(base) / APP_ID


class ProfileStore:
    """Load and save user-created conversion profiles."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or profile_config_dir() / "profiles.json"

    def built_in_profiles(self) -> list[ConversionProfile]:
        return list(default_profiles())

    def user_profiles(self) -> list[ConversionProfile]:
        if not self.path.exists():
            return []
        return [
            profile for profile in import_profiles(self.path) if not profile.built_in
        ]

    def all_profiles(self) -> list[ConversionProfile]:
        profiles = self.built_in_profiles()
        profiles.extend(self.user_profiles())
        return profiles

    def save_user_profiles(self, profiles: list[ConversionProfile]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        export_profiles(
            self.path, [profile for profile in profiles if not profile.built_in]
        )

    def add_or_replace_user_profile(self, profile: ConversionProfile) -> None:
        if profile.built_in:
            raise ValueError("Built-in profiles cannot be saved as user profiles.")
        profiles = [
            item
            for item in self.user_profiles()
            if item.identifier != profile.identifier
        ]
        profiles.append(profile)
        self.save_user_profiles(profiles)

    def delete_user_profile(self, identifier: str) -> bool:
        profiles = self.user_profiles()
        kept = [profile for profile in profiles if profile.identifier != identifier]
        if len(kept) == len(profiles):
            return False
        self.save_user_profiles(kept)
        return True

    def restore_defaults(self) -> None:
        self.save_user_profiles([])
