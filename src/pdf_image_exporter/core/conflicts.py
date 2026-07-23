"""Output file collision policies."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class FileConflictPolicy(str, Enum):
    """Supported actions when an output file already exists."""

    ASK = "ask"
    OVERWRITE = "overwrite"
    SKIP = "skip"
    AUTO_RENAME = "auto_rename"
    CANCEL = "cancel"


class CollisionAction(str, Enum):
    """Result of resolving an output path collision."""

    USE = "use"
    SKIP = "skip"
    CANCEL = "cancel"


def resolve_output_path(
    desired_path: Path,
    policy: FileConflictPolicy,
    existing_paths: set[Path] | None = None,
) -> tuple[CollisionAction, Path]:
    """Resolve an output path according to a collision policy.

    ``existing_paths`` lets callers detect collisions between outputs planned in
    the same batch before any process starts.
    """

    seen = existing_paths if existing_paths is not None else set()
    collides = desired_path.exists() or desired_path in seen
    if not collides or policy is FileConflictPolicy.OVERWRITE:
        return CollisionAction.USE, desired_path
    if policy is FileConflictPolicy.SKIP:
        return CollisionAction.SKIP, desired_path
    if policy in {FileConflictPolicy.ASK, FileConflictPolicy.CANCEL}:
        return CollisionAction.CANCEL, desired_path
    return CollisionAction.USE, _auto_renamed_path(desired_path, seen)


def _auto_renamed_path(path: Path, existing_paths: set[Path]) -> Path:
    for index in range(1, 10_000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists() and candidate not in existing_paths:
            return candidate
    raise RuntimeError(f"Could not find an unused filename for {path}")
