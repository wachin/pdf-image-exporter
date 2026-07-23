from __future__ import annotations

from pathlib import Path

from pdf_image_exporter.services.thumbnail_service import (
    ThumbnailRequest,
    build_thumbnail_args,
)


def test_thumbnail_arguments_are_safe_list() -> None:
    args = build_thumbnail_args(
        ThumbnailRequest(Path("/tmp/a file.pdf"), page=2, max_pixels=320),
        Path("/tmp/cache/thumb"),
    )

    assert args == [
        "-png",
        "-f",
        "2",
        "-l",
        "2",
        "-singlefile",
        "-scale-to",
        "320",
        "/tmp/a file.pdf",
        "/tmp/cache/thumb",
    ]
