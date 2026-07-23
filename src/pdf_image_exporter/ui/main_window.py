"""Main application window for the first functional milestone."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QKeySequence, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QLineEdit,
    QFrame,
    QScrollArea,
    QInputDialog,
)

from ..core.conversion import ConversionSettings
from ..core.conflicts import FileConflictPolicy
from ..core.discovery import discover_pdf_files
from ..core.errors import user_error_message
from ..core.formats import FormatOptions, OutputFormat
from ..core.pdf_info import PdfDocumentInfo
from ..core.profiles import (
    ConversionProfile,
    default_profiles,
    export_profiles,
    import_profiles,
    profile_identifier_from_name,
)
from ..core.queue import QueueSettings, plan_conversions
from ..metadata import APP_NAME
from ..services.pdftocairo_service import ConversionQueueRunner, PageConversion
from ..services.pdfinfo_service import PdfInfoService
from ..services.logging_service import QtLogHandler
from ..services.profile_store import ProfileStore
from ..services.settings_service import SettingsService
from ..services.thumbnail_service import ThumbnailRequest, ThumbnailService
from ..services.translation_service import available_languages, normalized_language_code
from .dialogs.log_dialog import LogDialog

LOGGER = logging.getLogger("pdf_image_exporter.ui")


class MainWindow(QMainWindow):
    """Minimal GUI: add PDFs, inspect metadata, convert pages."""

    def __init__(
        self,
        log_handler: QtLogHandler | None = None,
        initial_paths: list[Path] | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self._documents: dict[Path, PdfDocumentInfo] = {}
        self._settings = SettingsService()
        self._profile_store = ProfileStore()
        self._profiles: list[ConversionProfile] = []
        self._log_handler = log_handler
        self._pdfinfo = PdfInfoService(self)
        self._runner = ConversionQueueRunner(self)
        self._thumbnail_service = ThumbnailService(self)
        self._preview_pixmap = QPixmap()
        self._preview_fit_to_window = True
        self._output_dir: Path | None = self._settings.last_output_dir()
        self.setAcceptDrops(True)
        self._build_ui()
        self._connect_signals()
        self._configure_accessibility()
        self.resize(self._settings.window_size(self.size()))
        self._restore_conversion_settings()
        if initial_paths:
            self._add_paths(initial_paths)

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        self.add_button = QPushButton(self.tr("Add PDF"))
        self.add_folder_button = QPushButton(self.tr("Add folder"))
        self.remove_button = QPushButton(self.tr("Remove"))
        self.up_button = QPushButton(self.tr("Up"))
        self.down_button = QPushButton(self.tr("Down"))
        self.log_button = QPushButton(self.tr("Log"))
        self.convert_button = QPushButton(self.tr("Convert"))
        self.pause_button = QPushButton(self.tr("Pause"))
        self.stop_after_current_button = QPushButton(self.tr("Stop after current"))
        self.retry_button = QPushButton(self.tr("Retry failed"))
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.pause_button.setEnabled(False)
        self.stop_after_current_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.add_folder_button)
        toolbar.addWidget(self.remove_button)
        toolbar.addWidget(self.up_button)
        toolbar.addWidget(self.down_button)
        toolbar.addWidget(self.log_button)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel(self.tr("Profile:")))
        self.profile_combo = QComboBox()
        self._load_profiles()
        toolbar.addWidget(self.profile_combo)
        self.save_profile_button = QPushButton(self.tr("Save profile"))
        self.import_profiles_button = QPushButton(self.tr("Import"))
        self.export_profiles_button = QPushButton(self.tr("Export"))
        self.delete_profile_button = QPushButton(self.tr("Delete"))
        self.restore_profiles_button = QPushButton(self.tr("Defaults"))
        toolbar.addWidget(self.save_profile_button)
        toolbar.addWidget(self.import_profiles_button)
        toolbar.addWidget(self.export_profiles_button)
        toolbar.addWidget(self.delete_profile_button)
        toolbar.addWidget(self.restore_profiles_button)
        toolbar.addWidget(QLabel(self.tr("Language:")))
        self.language_combo = QComboBox()
        for language in available_languages():
            self.language_combo.addItem(language.name, language.code)
        toolbar.addWidget(self.language_combo)
        toolbar.addWidget(QLabel(self.tr("Format:")))
        self.format_combo = QComboBox()
        self.format_combo.addItem("PNG", OutputFormat.PNG.value)
        self.format_combo.addItem("JPEG", OutputFormat.JPEG.value)
        self.format_combo.addItem("TIFF", OutputFormat.TIFF.value)
        toolbar.addWidget(self.format_combo)
        toolbar.addWidget(QLabel(self.tr("DPI:")))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(1, 2400)
        self.dpi_spin.setValue(150)
        toolbar.addWidget(self.dpi_spin)
        toolbar.addWidget(QLabel(self.tr("Pages:")))
        self.pages_edit = QLineEdit("all")
        self.pages_edit.setPlaceholderText(self.tr("all, 1, 2-5, odd, even"))
        self.pages_edit.setMaximumWidth(170)
        toolbar.addWidget(self.pages_edit)
        self.recursive_check = QCheckBox(self.tr("Recursive"))
        toolbar.addWidget(self.recursive_check)
        toolbar.addWidget(QLabel(self.tr("Existing:")))
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem(self.tr("Cancel"), FileConflictPolicy.CANCEL.value)
        self.conflict_combo.addItem(self.tr("Skip"), FileConflictPolicy.SKIP.value)
        self.conflict_combo.addItem(
            self.tr("Auto rename"), FileConflictPolicy.AUTO_RENAME.value
        )
        self.conflict_combo.addItem(
            self.tr("Overwrite"), FileConflictPolicy.OVERWRITE.value
        )
        toolbar.addWidget(self.conflict_combo)
        toolbar.addWidget(QLabel(self.tr("Parallel:")))
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 4)
        self.parallel_spin.setValue(1)
        toolbar.addWidget(self.parallel_spin)
        self.output_button = QPushButton(self.tr("Output folder"))
        toolbar.addWidget(self.output_button)
        toolbar.addWidget(self.convert_button)
        toolbar.addWidget(self.pause_button)
        toolbar.addWidget(self.stop_after_current_button)
        toolbar.addWidget(self.retry_button)
        toolbar.addWidget(self.cancel_button)
        root.addLayout(toolbar)

        content = QHBoxLayout()
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Name"),
                self.tr("Path"),
                self.tr("Pages"),
                self.tr("Page size"),
                self.tr("Status"),
                self.tr("Output"),
            ]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        content.addWidget(self.table, 3)

        preview_panel = QVBoxLayout()
        preview_title = QLabel(self.tr("Preview"))
        preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_controls = QHBoxLayout()
        preview_controls.addWidget(QLabel(self.tr("Page:")))
        self.preview_page_spin = QSpinBox()
        self.preview_page_spin.setRange(1, 1)
        preview_controls.addWidget(self.preview_page_spin)
        preview_controls.addWidget(QLabel(self.tr("Zoom:")))
        self.preview_zoom_spin = QSpinBox()
        self.preview_zoom_spin.setRange(25, 400)
        self.preview_zoom_spin.setSingleStep(25)
        self.preview_zoom_spin.setValue(100)
        preview_controls.addWidget(self.preview_zoom_spin)
        self.preview_fit_button = QPushButton(self.tr("Fit"))
        preview_controls.addWidget(self.preview_fit_button)
        self.preview_label = QLabel(self.tr("Select a PDF"))
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFrameShape(QFrame.Shape.StyledPanel)
        self.preview_label.setMinimumSize(260, 320)
        self.preview_label.setScaledContents(False)
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidget(self.preview_label)
        self.preview_scroll.setWidgetResizable(True)
        self.preview_info_label = QLabel("")
        self.preview_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_panel.addWidget(preview_title)
        preview_panel.addLayout(preview_controls)
        preview_panel.addWidget(self.preview_scroll, 1)
        preview_panel.addWidget(self.preview_info_label)
        content.addLayout(preview_panel, 1)
        root.addLayout(content, 1)

        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.status_label = QLabel(self.tr("Ready"))
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.status_label)
        root.addLayout(bottom)
        self.setCentralWidget(central)

    def _configure_accessibility(self) -> None:
        self.add_button.setShortcut(QKeySequence.StandardKey.Open)
        self.remove_button.setShortcut(QKeySequence.StandardKey.Delete)
        self.convert_button.setShortcut("Ctrl+Return")
        self.cancel_button.setShortcut(QKeySequence.StandardKey.Cancel)
        self.log_button.setShortcut("Ctrl+L")
        self.output_button.setShortcut("Ctrl+O")
        self.preview_fit_button.setShortcut("Ctrl+0")

        labelled_widgets = {
            self.add_button: self.tr("Add PDF files to the conversion queue"),
            self.add_folder_button: self.tr("Add a folder of PDF files"),
            self.remove_button: self.tr("Remove selected PDF files"),
            self.up_button: self.tr("Move selected PDF files up"),
            self.down_button: self.tr("Move selected PDF files down"),
            self.log_button: self.tr("Open the activity log"),
            self.profile_combo: self.tr("Conversion profile"),
            self.language_combo: self.tr("Interface language"),
            self.format_combo: self.tr("Output image format"),
            self.dpi_spin: self.tr("Rasterization resolution in DPI"),
            self.pages_edit: self.tr("Page range expression"),
            self.recursive_check: self.tr("Import folders recursively"),
            self.conflict_combo: self.tr("Output file conflict policy"),
            self.parallel_spin: self.tr("Maximum simultaneous conversion processes"),
            self.output_button: self.tr("Choose output folder"),
            self.convert_button: self.tr("Start conversion"),
            self.pause_button: self.tr("Pause or resume conversion"),
            self.stop_after_current_button: self.tr("Stop after current page batch"),
            self.retry_button: self.tr("Retry failed pages"),
            self.cancel_button: self.tr("Cancel running conversions"),
            self.table: self.tr("PDF conversion queue"),
            self.preview_page_spin: self.tr("Preview page number"),
            self.preview_zoom_spin: self.tr("Preview zoom percentage"),
            self.preview_fit_button: self.tr("Fit preview to window"),
            self.preview_label: self.tr("PDF page preview"),
            self.progress: self.tr("Overall conversion progress"),
            self.status_label: self.tr("Current status"),
        }
        for widget, text in labelled_widgets.items():
            widget.setAccessibleName(text)
            widget.setToolTip(text)

        self.setTabOrder(self.add_button, self.add_folder_button)
        self.setTabOrder(self.add_folder_button, self.remove_button)
        self.setTabOrder(self.remove_button, self.up_button)
        self.setTabOrder(self.up_button, self.down_button)
        self.setTabOrder(self.down_button, self.log_button)
        self.setTabOrder(self.log_button, self.profile_combo)
        self.setTabOrder(self.profile_combo, self.save_profile_button)
        self.setTabOrder(self.save_profile_button, self.language_combo)
        self.setTabOrder(self.language_combo, self.format_combo)
        self.setTabOrder(self.format_combo, self.dpi_spin)
        self.setTabOrder(self.dpi_spin, self.pages_edit)
        self.setTabOrder(self.pages_edit, self.recursive_check)
        self.setTabOrder(self.recursive_check, self.conflict_combo)
        self.setTabOrder(self.conflict_combo, self.parallel_spin)
        self.setTabOrder(self.parallel_spin, self.output_button)
        self.setTabOrder(self.output_button, self.convert_button)
        self.setTabOrder(self.convert_button, self.pause_button)
        self.setTabOrder(self.pause_button, self.stop_after_current_button)
        self.setTabOrder(self.stop_after_current_button, self.retry_button)
        self.setTabOrder(self.retry_button, self.cancel_button)

    def _connect_signals(self) -> None:
        self.add_button.clicked.connect(self._add_pdf)
        self.add_folder_button.clicked.connect(self._add_folder)
        self.remove_button.clicked.connect(self._remove_selected)
        self.up_button.clicked.connect(self._move_selected_up)
        self.down_button.clicked.connect(self._move_selected_down)
        self.log_button.clicked.connect(self._show_log)
        self.output_button.clicked.connect(self._choose_output)
        self.convert_button.clicked.connect(self._convert)
        self.pause_button.clicked.connect(self._toggle_pause)
        self.stop_after_current_button.clicked.connect(self._stop_after_current)
        self.retry_button.clicked.connect(self._retry_failed)
        self.cancel_button.clicked.connect(self._runner.cancel)
        self.save_profile_button.clicked.connect(self._save_current_profile)
        self.import_profiles_button.clicked.connect(self._import_profiles)
        self.export_profiles_button.clicked.connect(self._export_profiles)
        self.delete_profile_button.clicked.connect(self._delete_current_profile)
        self.restore_profiles_button.clicked.connect(self._restore_default_profiles)
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        self._pdfinfo.finished.connect(self._pdfinfo_finished)
        self._pdfinfo.failed.connect(self._pdfinfo_failed)
        self._runner.progressChanged.connect(self._progress_changed)
        self._runner.finished.connect(self._conversion_finished)
        self._runner.finishedWithWarnings.connect(
            self._conversion_finished_with_warnings
        )
        self._runner.failed.connect(self._conversion_failed)
        self._runner.canceled.connect(self._conversion_canceled)
        self._runner.paused.connect(self._conversion_paused)
        self._runner.resumed.connect(self._conversion_resumed)
        self._runner.stoppedAfterCurrent.connect(self._stopped_after_current)
        self._runner.pageFailed.connect(self._page_failed)
        self._thumbnail_service.ready.connect(self._thumbnail_ready)
        self._thumbnail_service.failed.connect(self._thumbnail_failed)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.preview_page_spin.valueChanged.connect(self._preview_page_changed)
        self.preview_zoom_spin.valueChanged.connect(self._preview_zoom_changed)
        self.preview_fit_button.clicked.connect(self._fit_preview)

    def _add_pdf(self) -> None:
        files, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            self.tr("Add PDF files"),
            "",
            self.tr("PDF files (*.pdf);;All files (*)"),
        )
        self._add_paths([Path(filename) for filename in files])

    def _add_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, self.tr("Add PDF folder"))
        if not directory:
            return
        try:
            paths = discover_pdf_files(
                Path(directory), self.recursive_check.isChecked()
            )
        except OSError as exc:
            QMessageBox.warning(self, APP_NAME, user_error_message(exc))
            LOGGER.warning("Folder import failed: %s", exc)
            return
        self._add_paths(paths)

    def _remove_selected(self) -> None:
        rows = sorted(
            {index.row() for index in self.table.selectedIndexes()}, reverse=True
        )
        for row in rows:
            path = Path(self.table.item(row, 1).text())
            self._documents.pop(path, None)
            self.table.removeRow(row)

    def _move_selected_up(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        self.table.clearSelection()
        for row in rows:
            if row > 0:
                self._swap_rows(row, row - 1)
                self.table.selectRow(row - 1)

    def _move_selected_down(self) -> None:
        rows = sorted(
            {index.row() for index in self.table.selectedIndexes()}, reverse=True
        )
        self.table.clearSelection()
        for row in rows:
            if row < self.table.rowCount() - 1:
                self._swap_rows(row, row + 1)
                self.table.selectRow(row + 1)

    def _choose_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, self.tr("Choose output folder")
        )
        if directory:
            self._output_dir = Path(directory)
            self._settings.set_last_output_dir(self._output_dir)
            for row in range(self.table.rowCount()):
                self.table.setItem(row, 5, QTableWidgetItem(directory))

    def _convert(self) -> None:
        if not self._documents:
            QMessageBox.information(
                self, APP_NAME, self.tr("Add at least one PDF first.")
            )
            return
        output_dir = self._output_dir
        if output_dir is None:
            QMessageBox.information(
                self, APP_NAME, self.tr("Choose an output folder first.")
            )
            return
        output_format = OutputFormat(self.format_combo.currentData())
        settings = ConversionSettings(
            output_format=output_format,
            dpi=self.dpi_spin.value(),
            page_expression=self.pages_edit.text(),
            output_dir=output_dir,
            format_options=FormatOptions(output_format=output_format),
        )
        try:
            plan = plan_conversions(
                self._ordered_documents(),
                settings,
                FileConflictPolicy(self.conflict_combo.currentData()),
            )
        except (FileExistsError, ValueError) as exc:
            QMessageBox.warning(self, APP_NAME, user_error_message(exc))
            LOGGER.warning("Conversion planning failed: %s", exc)
            return
        warning = plan.resource_warning()
        if warning is not None:
            QMessageBox.warning(self, APP_NAME, warning)
        requests = [
            PageConversion.from_planned_page(page, job.settings)
            for job in plan.jobs
            for page in job.pages
        ]
        if not requests:
            QMessageBox.information(
                self,
                APP_NAME,
                self.tr("There are no pages to convert with the current settings."),
            )
            return
        self.convert_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_after_current_button.setEnabled(True)
        self.retry_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText(self.tr("Converting"))
        self._save_conversion_settings()
        LOGGER.info("Starting conversion of %s page(s)", len(requests))
        self._runner.start(
            requests,
            QueueSettings(max_parallel_processes=self.parallel_spin.value()),
        )

    def _profile_changed(self) -> None:
        selected = self.profile_combo.currentData()
        for profile in self._profiles:
            if profile.identifier == selected:
                self.format_combo.setCurrentIndex(
                    self.format_combo.findData(profile.settings.output_format.value)
                )
                self.dpi_spin.setValue(profile.settings.dpi)
                self.pages_edit.setText(profile.settings.page_expression)
                return

    def _load_profiles(self, selected_identifier: str | None = None) -> None:
        try:
            self._profiles = self._profile_store.all_profiles()
        except (OSError, ValueError) as exc:
            LOGGER.warning("Could not load user profiles: %s", exc)
            self._profiles = list(default_profiles())
        current = selected_identifier or self.profile_combo.currentData()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in self._profiles:
            label = profile.name if profile.built_in else f"{profile.name} *"
            self.profile_combo.addItem(label, profile.identifier)
        if current is not None:
            index = self.profile_combo.findData(current)
            if index >= 0:
                self.profile_combo.setCurrentIndex(index)
        self.profile_combo.blockSignals(False)

    def _current_conversion_settings(self) -> ConversionSettings:
        output_format = OutputFormat(self.format_combo.currentData())
        return ConversionSettings(
            output_format=output_format,
            dpi=self.dpi_spin.value(),
            page_expression=self.pages_edit.text(),
            output_dir=self._output_dir,
            format_options=FormatOptions(output_format=output_format),
        )

    def _save_current_profile(self) -> None:
        name, accepted = QInputDialog.getText(self, APP_NAME, self.tr("Profile name:"))
        if not accepted or not name.strip():
            return
        profile = ConversionProfile(
            identifier=profile_identifier_from_name(name),
            name=name.strip(),
            description=name.strip(),
            settings=self._current_conversion_settings(),
            built_in=False,
        )
        try:
            self._profile_store.add_or_replace_user_profile(profile)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self._load_profiles(profile.identifier)
        self.profile_combo.setCurrentIndex(
            self.profile_combo.findData(profile.identifier)
        )

    def _import_profiles(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self.tr("Import profiles"),
            "",
            self.tr("JSON files (*.json);;All files (*)"),
        )
        if not filename:
            return
        try:
            profiles = [
                ConversionProfile(
                    identifier=profile.identifier,
                    name=profile.name,
                    description=profile.description,
                    settings=profile.settings,
                    built_in=False,
                )
                for profile in import_profiles(Path(filename))
            ]
            for profile in profiles:
                self._profile_store.add_or_replace_user_profile(profile)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self._load_profiles()

    def _export_profiles(self) -> None:
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            self.tr("Export user profiles"),
            "profiles.json",
            self.tr("JSON files (*.json);;All files (*)"),
        )
        if not filename:
            return
        try:
            export_profiles(Path(filename), self._profile_store.user_profiles())
        except OSError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))

    def _delete_current_profile(self) -> None:
        identifier = str(self.profile_combo.currentData())
        profile = next(
            (item for item in self._profiles if item.identifier == identifier),
            None,
        )
        if profile is None:
            return
        if profile.built_in:
            QMessageBox.information(
                self,
                APP_NAME,
                self.tr("Built-in profiles cannot be deleted."),
            )
            return
        if self._profile_store.delete_user_profile(identifier):
            self._load_profiles("screen-messaging")

    def _restore_default_profiles(self) -> None:
        self._profile_store.restore_defaults()
        self._load_profiles("screen-messaging")

    def _pdfinfo_finished(self, path: Path, info: object) -> None:
        assert isinstance(info, PdfDocumentInfo)
        self._documents[path] = info
        row = self._row_for_path(path)
        if row is not None:
            self._set_row(
                row,
                path,
                str(info.pages),
                info.display_size_summary(),
                self.tr("Ready"),
                str(self._output_dir or ""),
            )
            if info.has_mixed_page_sizes:
                self.table.item(row, 4).setText(self.tr("Ready - mixed sizes"))
            if self.table.currentRow() < 0:
                self.table.selectRow(row)

    def _pdfinfo_failed(self, path: Path, message: str) -> None:
        row = self._row_for_path(path)
        if row is not None:
            self.table.setItem(
                row,
                4,
                QTableWidgetItem(self.tr("Failed: {message}").format(message=message)),
            )

    def _progress_changed(self, done: int, total: int) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        self.status_label.setText(
            self.tr("{done} of {total} pages").format(done=done, total=total)
        )

    def _conversion_finished(self) -> None:
        self.convert_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText(self.tr("Pause"))
        self.stop_after_current_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.status_label.setText(self.tr("Completed"))
        LOGGER.info("Conversion completed")

    def _conversion_finished_with_warnings(self, failed_count: int) -> None:
        self.convert_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText(self.tr("Pause"))
        self.stop_after_current_button.setEnabled(False)
        self.retry_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText(
            self.tr("Completed with {count} failed page(s)").format(count=failed_count)
        )
        LOGGER.warning("Conversion completed with %s failed page(s)", failed_count)

    def _conversion_failed(self, message: str) -> None:
        self.convert_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText(self.tr("Pause"))
        self.stop_after_current_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        QMessageBox.critical(self, APP_NAME, message)
        self.status_label.setText(self.tr("Failed"))
        LOGGER.error("Conversion failed: %s", message)

    def _conversion_canceled(self) -> None:
        self.convert_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText(self.tr("Pause"))
        self.stop_after_current_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.status_label.setText(self.tr("Canceled"))
        LOGGER.warning("Conversion canceled")

    def _conversion_paused(self) -> None:
        self.pause_button.setText(self.tr("Resume"))
        self.status_label.setText(self.tr("Paused after running page(s) finish"))
        LOGGER.info("Conversion queue paused")

    def _conversion_resumed(self) -> None:
        self.pause_button.setText(self.tr("Pause"))
        self.status_label.setText(self.tr("Converting"))
        LOGGER.info("Conversion queue resumed")

    def _page_failed(self, page: int, message: str) -> None:
        LOGGER.error("Page %s failed: %s", page, message)

    def _stopped_after_current(self) -> None:
        self.convert_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText(self.tr("Pause"))
        self.stop_after_current_button.setEnabled(False)
        self.retry_button.setEnabled(self._runner.failed_count > 0)
        self.cancel_button.setEnabled(False)
        self.status_label.setText(self.tr("Stopped after current page(s)"))
        LOGGER.info("Conversion queue stopped after current page(s)")

    def _toggle_pause(self) -> None:
        if self._runner.is_paused:
            self._runner.resume()
        else:
            self._runner.pause()

    def _stop_after_current(self) -> None:
        self.stop_after_current_button.setEnabled(False)
        self.status_label.setText(self.tr("Stopping after current page(s)"))
        self._runner.request_stop_after_current()

    def _retry_failed(self) -> None:
        self.convert_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_after_current_button.setEnabled(True)
        self.retry_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText(self.tr("Retrying failed page(s)"))
        self._runner.retry_failed()

    def _show_log(self) -> None:
        if self._log_handler is None:
            QMessageBox.information(
                self, APP_NAME, self.tr("Logging is not configured.")
            )
            return
        dialog = LogDialog(self._log_handler, self)
        dialog.exec()

    def _restore_conversion_settings(self) -> None:
        profile_index = self.profile_combo.findData(self._settings.selected_profile())
        if profile_index >= 0:
            self.profile_combo.setCurrentIndex(profile_index)
        language_index = self.language_combo.findData(
            normalized_language_code(self._settings.language_code())
        )
        if language_index >= 0:
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(language_index)
            self.language_combo.blockSignals(False)
        format_index = self.format_combo.findData(self._settings.output_format().value)
        if format_index >= 0:
            self.format_combo.setCurrentIndex(format_index)
        self.dpi_spin.setValue(self._settings.dpi())
        self.pages_edit.setText(self._settings.page_expression())
        self.parallel_spin.setValue(self._settings.parallel_processes())
        self.recursive_check.setChecked(self._settings.recursive_folder_import())
        conflict_index = self.conflict_combo.findData(
            self._settings.conflict_policy().value
        )
        if conflict_index >= 0:
            self.conflict_combo.setCurrentIndex(conflict_index)

    def _save_conversion_settings(self) -> None:
        self._settings.set_selected_profile(str(self.profile_combo.currentData()))
        self._settings.set_output_format(OutputFormat(self.format_combo.currentData()))
        self._settings.set_dpi(self.dpi_spin.value())
        self._settings.set_page_expression(self.pages_edit.text())
        self._settings.set_parallel_processes(self.parallel_spin.value())
        self._settings.set_recursive_folder_import(self.recursive_check.isChecked())
        self._settings.set_language_code(str(self.language_combo.currentData()))
        self._settings.set_conflict_policy(
            FileConflictPolicy(self.conflict_combo.currentData())
        )
        self._settings.sync()

    def _language_changed(self) -> None:
        self._settings.set_language_code(str(self.language_combo.currentData()))
        self._settings.sync()
        QMessageBox.information(
            self,
            APP_NAME,
            self.tr(
                "Language changes will be applied after restarting the application."
            ),
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            if any(path.lower().endswith(".pdf") for path in paths):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.toLocalFile().lower().endswith(".pdf")
        ]
        self._add_paths(paths)
        event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._settings.set_window_size(self.size())
        self._save_conversion_settings()
        self._thumbnail_service.cleanup()
        super().closeEvent(event)

    def _row_for_path(self, path: Path) -> int | None:
        for row in range(self.table.rowCount()):
            if Path(self.table.item(row, 1).text()) == path:
                return row
        return None

    def _set_row(
        self,
        row: int,
        path: Path,
        pages: str,
        page_size: str,
        status: str,
        output: str,
    ) -> None:
        values = [path.name, str(path), pages, page_size, status, output]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, column, item)

    def _swap_rows(self, first: int, second: int) -> None:
        first_values = [
            self.table.item(first, column).text()
            for column in range(self.table.columnCount())
        ]
        second_values = [
            self.table.item(second, column).text()
            for column in range(self.table.columnCount())
        ]
        for column, value in enumerate(second_values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(first, column, item)
        for column, value in enumerate(first_values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(second, column, item)

    def _ordered_documents(self) -> list[PdfDocumentInfo]:
        documents: list[PdfDocumentInfo] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            info = self._documents.get(Path(item.text()))
            if info is not None:
                documents.append(info)
        return documents

    def _selection_changed(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.preview_label.setText(self.tr("Select a PDF"))
            self.preview_label.setPixmap(QPixmap())
            self.preview_info_label.setText("")
            self._preview_pixmap = QPixmap()
            return
        path_item = self.table.item(row, 1)
        path = Path(path_item.text())
        info = self._documents.get(path)
        if info is None:
            self.preview_label.setText(self.tr("Waiting for PDF analysis"))
            self.preview_label.setPixmap(QPixmap())
            self.preview_info_label.setText("")
            self._preview_pixmap = QPixmap()
            return
        self.preview_page_spin.blockSignals(True)
        self.preview_page_spin.setRange(1, max(info.pages, 1))
        self.preview_page_spin.setValue(1)
        self.preview_page_spin.blockSignals(False)
        self._request_preview(path, 1)

    def _thumbnail_ready(self, pdf_path: Path, page: int, image_path: Path) -> None:
        row = self.table.currentRow()
        if row < 0 or Path(self.table.item(row, 1).text()) != pdf_path:
            return
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.preview_label.setText(self.tr("Preview unavailable"))
            return
        self._preview_pixmap = pixmap
        self._apply_preview_pixmap()
        self.preview_info_label.setText(self.tr("Page {page}").format(page=page))
        self._update_preview_info(pdf_path, page)

    def _thumbnail_failed(self, pdf_path: Path, page: int, message: str) -> None:
        row = self.table.currentRow()
        if row >= 0 and Path(self.table.item(row, 1).text()) == pdf_path:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(self.tr("Preview unavailable"))
        LOGGER.warning(
            "Thumbnail failed for %s page %s: %s", pdf_path.name, page, message
        )

    def _preview_page_changed(self, page: int) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        self._request_preview(Path(self.table.item(row, 1).text()), page)

    def _preview_zoom_changed(self) -> None:
        self._preview_fit_to_window = False
        self.preview_scroll.setWidgetResizable(False)
        self._apply_preview_pixmap()

    def _fit_preview(self) -> None:
        self._preview_fit_to_window = True
        self.preview_scroll.setWidgetResizable(True)
        self._apply_preview_pixmap()

    def _request_preview(self, path: Path, page: int) -> None:
        self._preview_pixmap = QPixmap()
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(self.tr("Generating preview"))
        info = self._documents.get(path)
        pages = info.pages if info is not None else page
        self.preview_info_label.setText(
            self.tr("Page {page} of {pages}").format(page=page, pages=pages)
        )
        self._thumbnail_service.request(
            ThumbnailRequest(pdf_path=path, page=page, max_pixels=900)
        )

    def _apply_preview_pixmap(self) -> None:
        if self._preview_pixmap.isNull():
            return
        if self._preview_fit_to_window:
            scaled = self._preview_pixmap.scaled(
                self.preview_scroll.viewport().size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            zoom = self.preview_zoom_spin.value() / 100.0
            scaled = self._preview_pixmap.scaled(
                round(self._preview_pixmap.width() * zoom),
                round(self._preview_pixmap.height() * zoom),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.preview_label.setText("")
        self.preview_label.setPixmap(scaled)
        self.preview_label.resize(scaled.size())

    def _update_preview_info(self, path: Path, page: int) -> None:
        info = self._documents.get(path)
        if info is None:
            return
        mixed = self.tr(" - mixed page sizes") if info.has_mixed_page_sizes else ""
        self.preview_info_label.setText(
            self.tr("Page {page} of {pages}: {size}{mixed}").format(
                page=page,
                pages=info.pages,
                size=info.display_page_size(page),
                mixed=mixed,
            )
        )

    def _add_paths(self, paths: list[Path]) -> None:
        for path in paths:
            if path in self._documents or not path.exists():
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._set_row(
                row,
                path,
                "",
                "",
                self.tr("Analyzing"),
                str(self._output_dir or ""),
            )
            LOGGER.info("Inspecting PDF: %s", path.name)
            self._pdfinfo.inspect(path)
