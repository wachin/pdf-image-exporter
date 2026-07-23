from __future__ import annotations

from pathlib import Path

import pytest

from pdf_image_exporter.core.conversion import ConversionSettings
from pdf_image_exporter.core.formats import OutputFormat
from pdf_image_exporter.core.queue import QueueSettings
from pdf_image_exporter.services.pdftocairo_service import (
    ConversionQueueRunner,
    PageConversion,
)


def test_queue_runner_reports_missing_pdftocairo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "pdf_image_exporter.services.pdftocairo_service.find_executable",
        lambda _name: None,
    )
    runner = ConversionQueueRunner()
    failures: list[str] = []
    runner.failed.connect(failures.append)

    runner.start([_request(tmp_path, 1)], QueueSettings(max_parallel_processes=1))

    assert failures == [
        "pdftocairo was not found. Install it with: sudo apt install poppler-utils"
    ]


def test_queue_runner_rejects_invalid_queue_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "pdf_image_exporter.services.pdftocairo_service.find_executable",
        lambda _name: Path("/bin/true"),
    )
    runner = ConversionQueueRunner()
    failures: list[str] = []
    runner.failed.connect(failures.append)

    runner.start([_request(tmp_path, 1)], QueueSettings(max_parallel_processes=5))

    assert failures == ["The initial queue limits parallel processes to 4."]


def test_queue_runner_pause_resume_state() -> None:
    runner = ConversionQueueRunner()
    paused: list[str] = []
    resumed: list[str] = []
    runner.paused.connect(lambda: paused.append("paused"))
    runner.resumed.connect(lambda: resumed.append("resumed"))

    runner.pause()
    runner.resume()

    assert paused == ["paused"]
    assert resumed == ["resumed"]


def _request(tmp_path: Path, page: int) -> PageConversion:
    return PageConversion(
        pdf_path=tmp_path / "input.pdf",
        page=page,
        output_prefix=tmp_path / f"out-{page:03d}",
        settings=ConversionSettings(output_format=OutputFormat.PNG),
    )
