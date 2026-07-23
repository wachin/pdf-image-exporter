"""Persistent settings backed by QSettings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import QSettings, QSize

from ..core.conflicts import FileConflictPolicy
from ..core.formats import OutputFormat


class SettingsService:
    """Small typed facade over QSettings."""

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings()

    def value(self, key: str, default: Any = None) -> Any:
        return self._settings.value(key, default)

    def set_value(self, key: str, value: Any) -> None:
        self._settings.setValue(key, value)

    def last_output_dir(self) -> Path | None:
        value = self.value("paths/last_output_dir", "")
        if not isinstance(value, str) or not value:
            return None
        return Path(value)

    def set_last_output_dir(self, path: Path) -> None:
        self.set_value("paths/last_output_dir", str(path))

    def selected_profile(self) -> str:
        value = self.value("conversion/profile", "screen-messaging")
        return str(value)

    def set_selected_profile(self, identifier: str) -> None:
        self.set_value("conversion/profile", identifier)

    def output_format(self) -> OutputFormat:
        value = self.value("conversion/format", OutputFormat.JPEG.value)
        try:
            return OutputFormat(str(value))
        except ValueError:
            return OutputFormat.JPEG

    def set_output_format(self, output_format: OutputFormat) -> None:
        self.set_value("conversion/format", output_format.value)

    def dpi(self) -> int:
        value = self.value("conversion/dpi", 150)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 150

    def set_dpi(self, dpi: int) -> None:
        self.set_value("conversion/dpi", dpi)

    def parallel_processes(self) -> int:
        value = self.value("conversion/parallel_processes", 1)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 1
        return min(max(parsed, 1), 4)

    def set_parallel_processes(self, count: int) -> None:
        self.set_value("conversion/parallel_processes", min(max(count, 1), 4))

    def page_expression(self) -> str:
        return str(self.value("conversion/page_expression", "all"))

    def set_page_expression(self, expression: str) -> None:
        self.set_value("conversion/page_expression", expression)

    def conflict_policy(self) -> FileConflictPolicy:
        value = self.value(
            "conversion/conflict_policy", FileConflictPolicy.CANCEL.value
        )
        try:
            return FileConflictPolicy(str(value))
        except ValueError:
            return FileConflictPolicy.CANCEL

    def set_conflict_policy(self, policy: FileConflictPolicy) -> None:
        self.set_value("conversion/conflict_policy", policy.value)

    def window_size(self, default: QSize) -> QSize:
        value = self.value("window/size", default)
        return value if isinstance(value, QSize) else default

    def set_window_size(self, size: QSize) -> None:
        self.set_value("window/size", size)

    def sync(self) -> None:
        self._settings.sync()
