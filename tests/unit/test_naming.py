from __future__ import annotations

from pathlib import Path

from pdf_image_exporter.core.formats import OutputFormat
from pdf_image_exporter.core.naming import NamingContext, build_output_path


def test_output_template_uses_zero_padded_page() -> None:
    path = build_output_path(
        Path("/tmp/out"),
        "{document}-pagina-{page}",
        NamingContext(
            document="informe final",
            page=7,
            pages=12,
            output_format=OutputFormat.PNG,
            width=2480,
            height=3508,
            dpi=300,
        ),
        3,
    )
    assert path == Path("/tmp/out/informe final-pagina-007.png")


def test_jpeg_extension_is_jpg() -> None:
    path = build_output_path(
        Path("/tmp/out"),
        "{document}-{format}",
        NamingContext("doc", 1, 1, OutputFormat.JPEG, 100, 100, 72),
    )
    assert path.name == "doc-jpeg.jpg"
