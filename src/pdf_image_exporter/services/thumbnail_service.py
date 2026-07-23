"""Low-resolution PDF thumbnail generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, QTemporaryDir, pyqtSignal

from .process_service import find_executable


@dataclass(frozen=True)
class ThumbnailRequest:
    """A single thumbnail request."""

    pdf_path: Path
    page: int = 1
    max_pixels: int = 360


def build_thumbnail_args(request: ThumbnailRequest, output_prefix: Path) -> list[str]:
    """Build `pdftocairo` arguments for a low-resolution PNG thumbnail."""

    return [
        "-png",
        "-f",
        str(request.page),
        "-l",
        str(request.page),
        "-singlefile",
        "-scale-to",
        str(request.max_pixels),
        str(request.pdf_path),
        str(output_prefix),
    ]


class ThumbnailService(QObject):
    """Generate cached thumbnails asynchronously with `pdftocairo`."""

    ready = pyqtSignal(Path, int, Path)
    failed = pyqtSignal(Path, int, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._temp_dir = QTemporaryDir()
        self._cache: dict[tuple[Path, int, int], Path] = {}
        self._processes: dict[QProcess, tuple[ThumbnailRequest, Path]] = {}

    def request(self, request: ThumbnailRequest) -> None:
        executable = find_executable("pdftocairo")
        if executable is None:
            self.failed.emit(
                request.pdf_path, request.page, "pdftocairo was not found."
            )
            return
        key = (request.pdf_path, request.page, request.max_pixels)
        cached = self._cache.get(key)
        if cached is not None and cached.exists():
            self.ready.emit(request.pdf_path, request.page, cached)
            return

        output_prefix = self._output_prefix(request)
        output_path = output_prefix.with_suffix(".png")
        process = QProcess(self)
        self._processes[process] = (request, output_path)
        process.finished.connect(
            lambda exit_code, status, p=process: self._finished(p, exit_code, status)
        )
        process.errorOccurred.connect(lambda _error, p=process: self._errored(p))
        process.start(str(executable), build_thumbnail_args(request, output_prefix))

    def cleanup(self) -> None:
        """Stop active thumbnail generation and remove the temporary directory."""

        for process in list(self._processes):
            process.kill()
            process.deleteLater()
        self._processes.clear()
        self._cache.clear()
        self._temp_dir.remove()

    def _output_prefix(self, request: ThumbnailRequest) -> Path:
        base = Path(self._temp_dir.path())
        safe_stem = f"{abs(hash(request.pdf_path))}-{request.page}-{request.max_pixels}"
        return base / safe_stem

    def _finished(
        self,
        process: QProcess,
        exit_code: int,
        _status: QProcess.ExitStatus,
    ) -> None:
        item = self._processes.pop(process, None)
        stderr = process.readAllStandardError().data().decode("utf-8", "replace")
        process.deleteLater()
        if item is None:
            return
        request, output_path = item
        if exit_code == 0 and output_path.exists():
            self._cache[
                (request.pdf_path, request.page, request.max_pixels)
            ] = output_path
            self.ready.emit(request.pdf_path, request.page, output_path)
            return
        self.failed.emit(
            request.pdf_path,
            request.page,
            stderr.strip() or "Thumbnail generation failed.",
        )

    def _errored(self, process: QProcess) -> None:
        item = self._processes.pop(process, None)
        if item is None:
            return
        request, _output_path = item
        message = process.errorString()
        process.deleteLater()
        self.failed.emit(request.pdf_path, request.page, message)
