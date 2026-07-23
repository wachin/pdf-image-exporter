from __future__ import annotations

from pathlib import Path

import pytest

from pdf_image_exporter.core.conflicts import FileConflictPolicy
from pdf_image_exporter.core.conversion import ConversionSettings
from pdf_image_exporter.core.dimensions import PageSize
from pdf_image_exporter.core.formats import OutputFormat
from pdf_image_exporter.core.pdf_info import PdfDocumentInfo
from pdf_image_exporter.core.queue import QueueSettings, plan_conversions


def test_plan_conversions_builds_pages(tmp_path: Path) -> None:
    info = PdfDocumentInfo(
        path=Path("/tmp/report.pdf"),
        pages=3,
        page_sizes=(PageSize(595, 842),),
    )
    plan = plan_conversions(
        [info],
        ConversionSettings(
            output_format=OutputFormat.PNG,
            dpi=300,
            page_expression="1,3",
            output_dir=tmp_path,
        ),
    )
    assert plan.page_count == 2
    assert [page.page for page in plan.pages] == [1, 3]
    assert plan.pages[0].output_path == tmp_path / "report-001.png"
    assert plan.pages[0].width == 2479


def test_plan_conversions_rejects_existing_output_by_default(tmp_path: Path) -> None:
    (tmp_path / "report-001.png").write_text("existing", "utf-8")
    info = PdfDocumentInfo(
        path=Path("/tmp/report.pdf"),
        pages=1,
        page_sizes=(PageSize(595, 842),),
    )
    with pytest.raises(FileExistsError):
        plan_conversions(
            [info],
            ConversionSettings(output_dir=tmp_path),
            FileConflictPolicy.CANCEL,
        )


def test_plan_conversions_auto_renames_existing_output(tmp_path: Path) -> None:
    (tmp_path / "report-001.png").write_text("existing", "utf-8")
    info = PdfDocumentInfo(
        path=Path("/tmp/report.pdf"),
        pages=1,
        page_sizes=(PageSize(595, 842),),
    )
    plan = plan_conversions(
        [info],
        ConversionSettings(output_dir=tmp_path),
        FileConflictPolicy.AUTO_RENAME,
    )
    assert plan.pages[0].output_path == tmp_path / "report-001-1.png"


def test_queue_settings_limits_parallel_processes() -> None:
    QueueSettings(max_parallel_processes=4).validate()
    with pytest.raises(ValueError):
        QueueSettings(max_parallel_processes=0).validate()
    with pytest.raises(ValueError):
        QueueSettings(max_parallel_processes=5).validate()
