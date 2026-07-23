"""Main application window for the first functional milestone."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
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
)

from ..core.conversion import ConversionSettings
from ..core.formats import FormatOptions, OutputFormat
from ..core.naming import NamingContext, build_output_path
from ..core.page_ranges import parse_page_ranges
from ..core.pdf_info import PdfDocumentInfo
from ..metadata import APP_NAME
from ..services.pdftocairo_service import PageConversion, PdfToCairoRunner
from ..services.pdfinfo_service import PdfInfoService


class MainWindow(QMainWindow):
    """Minimal GUI: add PDFs, inspect metadata, convert pages."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 680)
        self._documents: dict[Path, PdfDocumentInfo] = {}
        self._pdfinfo = PdfInfoService(self)
        self._runner = PdfToCairoRunner(self)
        self._output_dir: Path | None = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        self.add_button = QPushButton(self.tr("Add PDF"))
        self.remove_button = QPushButton(self.tr("Remove"))
        self.convert_button = QPushButton(self.tr("Convert"))
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.setEnabled(False)
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.remove_button)
        toolbar.addStretch(1)
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
        self.output_button.clicked.connect(self._choose_output)
        self.convert_button.clicked.connect(self._convert)
        self.cancel_button.clicked.connect(self._runner.cancel)
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
        for filename in files:
            path = Path(filename)
            if path in self._documents:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._set_row(row, path, "", "", self.tr("Analyzing"), "")
            self._pdfinfo.inspect(path)

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
            output_dir=output_dir,
            format_options=FormatOptions(output_format=output_format),
        )
        requests: list[PageConversion] = []
        for info in self._documents.values():
            pages = parse_page_ranges("all", info.pages)
            page_size = info.primary_page_size
            for page in pages:
                width = height = 0
                if page_size is not None:
                    width, height = page_size.pixels_at(settings.dpi)
                target = build_output_path(
                    output_dir,
                    settings.name_template,
                    NamingContext(
                        document=info.path.stem,
                        page=page,
                        pages=info.pages,
                        output_format=output_format,
                        width=width,
                        height=height,
                        dpi=settings.dpi,
                    ),
                    settings.page_digits,
                )
                if target.exists():
                    QMessageBox.warning(
                        self,
                        APP_NAME,
                        self.tr(
                            "Output already exists and will not be overwritten:\n{path}"
                        ).format(path=str(target)),
                    )
                    return
                requests.append(
                    PageConversion(
                        pdf_path=info.path,
                        page=page,
                        output_prefix=target.with_suffix(""),
                        settings=settings,
                    )
                )
        self.convert_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText(self.tr("Converting"))
        self._runner.start(requests)

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

    def _conversion_failed(self, message: str) -> None:
        self.convert_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        QMessageBox.critical(self, APP_NAME, message)
        self.status_label.setText(self.tr("Failed"))

    def _conversion_canceled(self) -> None:
        self.convert_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText(self.tr("Canceled"))

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
