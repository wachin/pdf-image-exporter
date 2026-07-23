"""Safe `pdftocairo` argument construction and QProcess execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from ..core.conversion import ConversionSettings
from ..core.formats import FormatOptions, OutputFormat
from ..core.queue import PlannedPage, QueueSettings
from .process_service import find_executable


@dataclass(frozen=True)
class PageConversion:
    """A single page conversion request."""

    pdf_path: Path
    page: int
    output_prefix: Path
    settings: ConversionSettings

    @classmethod
    def from_planned_page(
        cls, planned_page: PlannedPage, settings: ConversionSettings
    ) -> "PageConversion":
        """Create a service request from a core conversion plan page."""

        return cls(
            pdf_path=planned_page.pdf_path,
            page=planned_page.page,
            output_prefix=planned_page.output_prefix,
            settings=settings,
        )


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


@dataclass(frozen=True)
class PageResult:
    """Result for a completed or failed page conversion."""

    request: PageConversion
    success: bool
    message: str = ""


class ConversionQueueRunner(QObject):
    """Run page conversions with bounded concurrency and failure collection."""

    pageStarted = pyqtSignal(int, int)
    pageFinished = pyqtSignal(int, Path)
    pageFailed = pyqtSignal(int, str)
    progressChanged = pyqtSignal(int, int)
    finished = pyqtSignal()
    finishedWithWarnings = pyqtSignal(int)
    failed = pyqtSignal(str)
    paused = pyqtSignal()
    resumed = pyqtSignal()
    canceled = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pending: list[PageConversion] = []
        self._failed_requests: list[PageConversion] = []
        self._active: dict[QProcess, PageConversion] = {}
        self._results: list[PageResult] = []
        self._settings = QueueSettings()
        self._total = 0
        self._done = 0
        self._paused = False
        self._cancel_requested = False
        self._executable: Path | None = None

    @property
    def is_running(self) -> bool:
        return bool(self._active)

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def failed_count(self) -> int:
        return len(self._failed_requests)

    def start(
        self,
        requests: list[PageConversion],
        settings: QueueSettings | None = None,
    ) -> None:
        if self._active:
            self.failed.emit("A conversion queue is already running.")
            return
        queue_settings = settings or QueueSettings()
        try:
            queue_settings.validate()
        except ValueError as exc:
            self.failed.emit(str(exc))
            return
        executable = find_executable("pdftocairo")
        if executable is None:
            self.failed.emit(
                "pdftocairo was not found. Install it with: sudo apt install poppler-utils"
            )
            return
        self._executable = executable
        self._settings = queue_settings
        self._pending = list(requests)
        self._failed_requests = []
        self._results = []
        self._total = len(self._pending)
        self._done = 0
        self._paused = False
        self._cancel_requested = False
        self.progressChanged.emit(self._done, self._total)
        self._fill_slots()

    def pause(self) -> None:
        if self._paused:
            return
        self._paused = True
        self.paused.emit()

    def resume(self) -> None:
        if not self._paused:
            return
        self._paused = False
        self.resumed.emit()
        self._fill_slots()

    def retry_failed(self) -> None:
        if self._active or not self._failed_requests:
            return
        requests = list(self._failed_requests)
        self.start(requests, self._settings)

    def cancel(self) -> None:
        self._cancel_requested = True
        self._pending.clear()
        for process in list(self._active):
            process.kill()
        if not self._active:
            self.canceled.emit()

    def _fill_slots(self) -> None:
        if self._paused or self._cancel_requested:
            return
        while (
            self._pending and len(self._active) < self._settings.max_parallel_processes
        ):
            request = self._pending.pop(0)
            self._start_request(request)
        self._maybe_finish()

    def _start_request(self, request: PageConversion) -> None:
        if self._executable is None:
            self.failed.emit("pdftocairo executable is not available.")
            return
        request.output_prefix.parent.mkdir(parents=True, exist_ok=True)
        process = QProcess(self)
        self._active[process] = request
        process.finished.connect(
            lambda exit_code, status, p=process: self._process_finished(
                p, exit_code, status
            )
        )
        process.errorOccurred.connect(lambda _error, p=process: self._process_error(p))
        self.pageStarted.emit(request.page, self._total)
        process.start(str(self._executable), build_pdftocairo_args(request))

    def _process_finished(
        self,
        process: QProcess,
        exit_code: int,
        _status: QProcess.ExitStatus,
    ) -> None:
        request = self._active.pop(process, None)
        stderr = process.readAllStandardError().data().decode("utf-8", "replace")
        process.deleteLater()
        if request is None:
            return
        if self._cancel_requested:
            self._done += 1
            self.progressChanged.emit(self._done, self._total)
            self._maybe_finish()
            return
        if exit_code == 0:
            self._results.append(PageResult(request=request, success=True))
            self.pageFinished.emit(request.page, request.output_prefix)
        else:
            message = stderr.strip() or "pdftocairo failed."
            self._results.append(
                PageResult(request=request, success=False, message=message)
            )
            self._failed_requests.append(request)
            self.pageFailed.emit(request.page, message)
        self._done += 1
        self.progressChanged.emit(self._done, self._total)
        self._fill_slots()

    def _process_error(self, process: QProcess) -> None:
        if self._cancel_requested:
            return
        request = self._active.pop(process, None)
        if request is None:
            return
        message = process.errorString()
        process.deleteLater()
        self._failed_requests.append(request)
        self._results.append(
            PageResult(request=request, success=False, message=message)
        )
        self.pageFailed.emit(request.page, message)
        self._done += 1
        self.progressChanged.emit(self._done, self._total)
        self._fill_slots()

    def _maybe_finish(self) -> None:
        if self._active or self._pending:
            return
        if self._cancel_requested:
            self.canceled.emit()
            return
        if self._failed_requests:
            self.finishedWithWarnings.emit(len(self._failed_requests))
            return
        self.finished.emit()
