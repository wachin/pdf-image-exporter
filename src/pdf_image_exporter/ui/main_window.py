"""Main application window for the first functional milestone."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QLineEdit,
)

from ..core.conversion import ConversionSettings
from ..core.conflicts import FileConflictPolicy
from ..core.formats import FormatOptions, OutputFormat
from ..core.pdf_info import PdfDocumentInfo
from ..core.profiles import default_profiles
from ..core.queue import plan_conversions
from ..metadata import APP_NAME
from ..services.pdftocairo_service import PageConversion, PdfToCairoRunner
from ..services.pdfinfo_service import PdfInfoService
from ..services.logging_service import QtLogHandler
from ..services.settings_service import SettingsService
from .dialogs.log_dialog import LogDialog

LOGGER = logging.getLogger("pdf_image_exporter.ui")


class MainWindow(QMainWindow):
    """Minimal GUI: add PDFs, inspect metadata, convert pages."""

    def __init__(self, log_handler: QtLogHandler | None = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self._documents: dict[Path, PdfDocumentInfo] = {}
        self._settings = SettingsService()
        self._log_handler = log_handler
        self._pdfinfo = PdfInfoService(self)
        self._runner = PdfToCairoRunner(self)
        self._output_dir: Path | None = self._settings.last_output_dir()
        self.setAcceptDrops(True)
        self._build_ui()
        self._connect_signals()
        self.resize(self._settings.window_size(self.size()))
        self._restore_conversion_settings()

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        self.add_button = QPushButton(self.tr("Add PDF"))
        self.remove_button = QPushButton(self.tr("Remove"))
        self.log_button = QPushButton(self.tr("Log"))
        self.convert_button = QPushButton(self.tr("Convert"))
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.setEnabled(False)
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.remove_button)
        toolbar.addWidget(self.log_button)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel(self.tr("Profile:")))
        self.profile_combo = QComboBox()
        for profile in default_profiles():
            self.profile_combo.addItem(profile.name, profile.identifier)
        toolbar.addWidget(self.profile_combo)
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
        self.output_button = QPushButton(self.tr("Output folder"))
        toolbar.addWidget(self.output_button)
        toolbar.addWidget(self.convert_button)
        toolbar.addWidget(self.cancel_button)
        root.addLayout(toolbar)

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
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.status_label = QLabel(self.tr("Ready"))
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.status_label)
        root.addLayout(bottom)
        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self.add_button.clicked.connect(self._add_pdf)
        self.remove_button.clicked.connect(self._remove_selected)
        self.log_button.clicked.connect(self._show_log)
        self.output_button.clicked.connect(self._choose_output)
        self.convert_button.clicked.connect(self._convert)
        self.cancel_button.clicked.connect(self._runner.cancel)
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        self._pdfinfo.finished.connect(self._pdfinfo_finished)
        self._pdfinfo.failed.connect(self._pdfinfo_failed)
        self._runner.progressChanged.connect(self._progress_changed)
        self._runner.finished.connect(self._conversion_finished)
        self._runner.failed.connect(self._conversion_failed)
        self._runner.canceled.connect(self._conversion_canceled)

    def _add_pdf(self) -> None:
        files, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            self.tr("Add PDF files"),
            "",
            self.tr("PDF files (*.pdf);;All files (*)"),
        )
        self._add_paths([Path(filename) for filename in files])

    def _remove_selected(self) -> None:
        rows = sorted(
            {index.row() for index in self.table.selectedIndexes()}, reverse=True
        )
        for row in rows:
            path = Path(self.table.item(row, 1).text())
            self._documents.pop(path, None)
            self.table.removeRow(row)

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
                list(self._documents.values()),
                settings,
                FileConflictPolicy.CANCEL,
            )
        except (FileExistsError, ValueError) as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
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
        self.cancel_button.setEnabled(True)
        self.status_label.setText(self.tr("Converting"))
        self._save_conversion_settings()
        LOGGER.info("Starting conversion of %s page(s)", len(requests))
        self._runner.start(requests)

    def _profile_changed(self) -> None:
        selected = self.profile_combo.currentData()
        for profile in default_profiles():
            if profile.identifier == selected:
                self.format_combo.setCurrentIndex(
                    self.format_combo.findData(profile.settings.output_format.value)
                )
                self.dpi_spin.setValue(profile.settings.dpi)
                self.pages_edit.setText(profile.settings.page_expression)
                return

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
        self.cancel_button.setEnabled(False)
        self.status_label.setText(self.tr("Completed"))
        LOGGER.info("Conversion completed")

    def _conversion_failed(self, message: str) -> None:
        self.convert_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        QMessageBox.critical(self, APP_NAME, message)
        self.status_label.setText(self.tr("Failed"))
        LOGGER.error("Conversion failed: %s", message)

    def _conversion_canceled(self) -> None:
        self.convert_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText(self.tr("Canceled"))
        LOGGER.warning("Conversion canceled")

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
        format_index = self.format_combo.findData(self._settings.output_format().value)
        if format_index >= 0:
            self.format_combo.setCurrentIndex(format_index)
        self.dpi_spin.setValue(self._settings.dpi())
        self.pages_edit.setText(self._settings.page_expression())

    def _save_conversion_settings(self) -> None:
        self._settings.set_selected_profile(str(self.profile_combo.currentData()))
        self._settings.set_output_format(OutputFormat(self.format_combo.currentData()))
        self._settings.set_dpi(self.dpi_spin.value())
        self._settings.set_page_expression(self.pages_edit.text())
        self._settings.sync()

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
