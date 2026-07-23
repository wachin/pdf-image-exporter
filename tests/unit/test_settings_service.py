from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings, QSize

from pdf_image_exporter.core.conflicts import FileConflictPolicy
from pdf_image_exporter.core.formats import OutputFormat
from pdf_image_exporter.services.settings_service import SettingsService


def test_settings_service_round_trip(tmp_path: Path) -> None:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    service = SettingsService(settings)

    service.set_last_output_dir(tmp_path)
    service.set_selected_profile("print-standard")
    service.set_output_format(OutputFormat.PNG)
    service.set_dpi(300)
    service.set_page_expression("1,3-4")
    service.set_conflict_policy(FileConflictPolicy.AUTO_RENAME)
    service.set_window_size(QSize(900, 700))
    service.sync()

    loaded = SettingsService(
        QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    )
    assert loaded.last_output_dir() == tmp_path
    assert loaded.selected_profile() == "print-standard"
    assert loaded.output_format() is OutputFormat.PNG
    assert loaded.dpi() == 300
    assert loaded.page_expression() == "1,3-4"
    assert loaded.conflict_policy() is FileConflictPolicy.AUTO_RENAME
    assert loaded.window_size(QSize(1, 1)) == QSize(900, 700)
