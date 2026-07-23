from __future__ import annotations

from pathlib import Path

from pdf_image_exporter.core.conversion import ConversionSettings
from pdf_image_exporter.core.formats import FormatOptions, OutputFormat
from pdf_image_exporter.services.pdftocairo_service import (
    PageConversion,
    build_pdftocairo_args,
)


def test_png_arguments_are_list_without_shell_fragments() -> None:
    request = PageConversion(
        pdf_path=Path("/tmp/a file.pdf"),
        page=3,
        output_prefix=Path("/tmp/out/a file-003"),
        settings=ConversionSettings(output_format=OutputFormat.PNG, dpi=300),
    )
    assert build_pdftocairo_args(request) == [
        "-png",
        "-f",
        "3",
        "-l",
        "3",
        "-singlefile",
        "-r",
        "300",
        "/tmp/a file.pdf",
        "/tmp/out/a file-003",
    ]


def test_jpeg_options_are_validated_into_single_jpegopt_argument() -> None:
    request = PageConversion(
        pdf_path=Path("/tmp/in.pdf"),
        page=1,
        output_prefix=Path("/tmp/out/in-001"),
        settings=ConversionSettings(
            output_format=OutputFormat.JPEG,
            dpi=150,
            format_options=FormatOptions(
                output_format=OutputFormat.JPEG,
                jpeg_quality=85,
                jpeg_progressive=True,
            ),
        ),
    )
    args = build_pdftocairo_args(request)
    assert "-jpegopt" in args
    assert "quality=85,progressive=y" in args
