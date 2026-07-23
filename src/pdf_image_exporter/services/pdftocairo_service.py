"""Safe `pdftocairo` argument construction and QProcess execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from ..core.conversion import ConversionSettings
from ..core.formats import FormatOptions, OutputFormat
from .process_service import find_executable


@dataclass(frozen=True)
class PageConversion:
    """A single page conversion request."""

    pdf_path: Path
    page: int
    output_prefix: Path
    settings: ConversionSettings


def build_pdftocairo_args(request: PageConversion) -> list[str]:
    """Build `pdftocairo` arguments as a list suitable for QProcess."""

    settings = request.settings
    settings.validate()
    options = settings.format_options
    args = [
        settings.output_format.pdftocairo_flag,
        "-f",
        str(request.page),
        "-l",
        str(request.page),
        "-singlefile",
        "-r",
        str(settings.dpi),
    ]
    args.extend(_format_args(settings.output_format, options))
    args.extend([str(request.pdf_path), str(request.output_prefix)])
    return args


def _format_args(output_format: OutputFormat, options: FormatOptions) -> list[str]:
    args: list[str] = []
    if options.monochrome:
        args.append("-mono")
    elif options.grayscale:
        args.append("-gray")
    if output_format is OutputFormat.PNG and options.transparent_background:
        args.append("-transp")
    if output_format is OutputFormat.JPEG:
        jpeg_opts = [f"quality={options.jpeg_quality}"]
        if options.jpeg_progressive:
            jpeg_opts.append("progressive=y")
        args.extend(["-jpegopt", ",".join(jpeg_opts)])
    if output_format is OutputFormat.TIFF:
        args.extend(["-tiffcompression", options.tiff_compression])
    return args


class PdfToCairoRunner(QObject):
    """Run page conversions sequentially through QProcess."""

    pageStarted = pyqtSignal(int, int)
    pageFinished = pyqtSignal(int, Path)
    progressChanged = pyqtSignal(int, int)
    finished = pyqtSignal()
    failed = pyqtSignal(str)
    canceled = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._queue: list[PageConversion] = []
        self._total = 0
        self._done = 0
        self._process: QProcess | None = None
        self._current: PageConversion | None = None
        self._cancel_requested = False

    def start(self, requests: list[PageConversion]) -> None:
        if self._process is not None:
            self.failed.emit("A conversion is already running.")
            return
        executable = find_executable("pdftocairo")
        if executable is None:
            self.failed.emit(
                "pdftocairo was not found. Install it with: sudo apt install poppler-utils"
            )
            return
        self._executable = executable
        self._queue = list(requests)
        self._total = len(self._queue)
        self._done = 0
        self._cancel_requested = False
        self.progressChanged.emit(self._done, self._total)
        self._start_next()

    def cancel(self) -> None:
        self._cancel_requested = True
        self._queue.clear()
        if self._process is not None:
            self._process.kill()
        else:
            self.canceled.emit()

    def _start_next(self) -> None:
        if self._cancel_requested:
            self._process = None
            self._current = None
            self.canceled.emit()
            return
        if not self._queue:
            self._process = None
            self._current = None
            self.finished.emit()
            return
        self._current = self._queue.pop(0)
        self._current.output_prefix.parent.mkdir(parents=True, exist_ok=True)
        process = QProcess(self)
        self._process = process
        process.finished.connect(self._process_finished)
        process.errorOccurred.connect(self._process_error)
        self.pageStarted.emit(self._current.page, self._total)
        process.start(str(self._executable), build_pdftocairo_args(self._current))

    def _process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        process = self._process
        current = self._current
        if process is None or current is None:
            return
        stderr = process.readAllStandardError().data().decode("utf-8", "replace")
        process.deleteLater()
        self._process = None
        if self._cancel_requested:
            self.canceled.emit()
            return
        if exit_code != 0:
            self.failed.emit(stderr.strip() or "pdftocairo failed.")
            return
        self._done += 1
        self.pageFinished.emit(current.page, current.output_prefix)
        self.progressChanged.emit(self._done, self._total)
        self._start_next()

    def _process_error(self, _error: QProcess.ProcessError) -> None:
        if self._cancel_requested:
            return
        process = self._process
        self.failed.emit(
            process.errorString() if process is not None else "Process error."
        )
