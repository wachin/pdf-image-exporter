"""Shared process helpers."""

from __future__ import annotations

from pathlib import Path
from shutil import which


def find_executable(name: str) -> Path | None:
    """Find an executable through the system PATH, excluding cwd-only results."""

    result = which(name)
    if result is None:
        return None
    path = Path(result).resolve()
    if path.parent == Path.cwd().resolve():
        return None
    return path
