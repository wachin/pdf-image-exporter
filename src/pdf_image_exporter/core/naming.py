"""Output filename template expansion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .formats import OutputFormat

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


@dataclass(frozen=True)
class NamingContext:
    """Values available to output filename templates."""

    document: str
    page: int
    pages: int
    output_format: OutputFormat
    width: int
    height: int
    dpi: int
    profile: str = "custom"


def build_output_path(
    output_dir: Path,
    template: str,
    context: NamingContext,
    page_digits: int = 3,
) -> Path:
    """Build a sanitized output path without overwriting policy decisions."""

    now = datetime.now()
    values = {
        "document": context.document,
        "page": str(context.page).zfill(page_digits),
        "pages": str(context.pages),
        "format": context.output_format.value,
        "width": str(context.width),
        "height": str(context.height),
        "dpi": str(context.dpi),
        "profile": context.profile,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H-%M-%S"),
    }
    name = template
    for key, value in values.items():
        name = name.replace("{" + key + "}", value)
    name = SAFE_NAME_RE.sub("_", name).strip(" .")
    if not name:
        name = f"{context.document}-{values['page']}"
    return output_dir / f"{name}.{context.output_format.extension}"
