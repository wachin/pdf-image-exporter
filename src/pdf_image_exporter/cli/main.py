"""Basic CLI entry point sharing core configuration."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..core.conversion import ConversionSettings
from ..core.formats import OutputFormat


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pdf-image-exporter-cli")
    parser.add_argument("pdf", type=Path)
    parser.add_argument(
        "--format", choices=[item.value for item in OutputFormat], default="png"
    )
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    settings = ConversionSettings(
        output_format=OutputFormat(args.format),
        dpi=args.dpi,
        output_dir=args.output_dir,
    )
    settings.validate()
    print(
        "CLI conversion execution is pending; parsed settings: "
        f"{args.pdf} -> {settings.output_format.value} at {settings.dpi} DPI"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
