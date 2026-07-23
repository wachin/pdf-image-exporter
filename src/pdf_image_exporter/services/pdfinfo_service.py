"""QProcess-backed `pdfinfo` service."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from ..core.pdf_info import PdfDocumentInfo, parse_pdfinfo_output
from .process_service import find_executable


class PdfInfoService(QObject):
    """Asynchronously inspect a PDF using `pdfinfo` without a shell."""

    finished = pyqtSignal(Path, object)
    failed = pyqtSignal(Path, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._processes: dict[QProcess, tuple[Path, bool]] = {}

    def inspect(self, pdf_path: Path) -> None:
        executable = find_executable("pdfinfo")
        if executable is None:
            self.failed.emit(pdf_path, "pdfinfo was not found. Install poppler-utils.")
            return
        self._start_process(executable, pdf_path, ["-box", "-isodates"], False)

    def _start_process(
        self,
        executable: Path,
        pdf_path: Path,
        arguments: list[str],
        page_detail: bool,
    ) -> None:
        process = QProcess(self)
        self._processes[process] = (pdf_path, page_detail)
        process.finished.connect(lambda _code, _status, p=process: self._finished(p))
        process.errorOccurred.connect(lambda _error, p=process: self._errored(p))
        process.start(str(executable), [*arguments, str(pdf_path)])

    def _finished(self, process: QProcess) -> None:
        path, page_detail = self._processes.pop(process)
        stdout = process.readAllStandardOutput().data().decode("utf-8", "replace")
        stderr = process.readAllStandardError().data().decode("utf-8", "replace")
        if process.exitCode() != 0:
            self.failed.emit(path, stderr.strip() or "pdfinfo failed.")
        else:
            info = parse_pdfinfo_output(path, stdout)
            executable = find_executable("pdfinfo")
            if (
                not page_detail
                and executable is not None
                and info.pages > 1
                and len(info.page_sizes) < info.pages
            ):
                self._start_process(
                    executable,
                    path,
                    ["-box", "-isodates", "-f", "1", "-l", str(info.pages)],
                    True,
                )
                process.deleteLater()
                return
            self.finished.emit(path, info)
        process.deleteLater()

    def _errored(self, process: QProcess) -> None:
        item = self._processes.get(process)
        if item is not None:
            self.failed.emit(item[0], process.errorString())
