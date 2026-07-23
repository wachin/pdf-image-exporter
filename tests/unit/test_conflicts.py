from __future__ import annotations

from pathlib import Path

from pdf_image_exporter.core.conflicts import (
    CollisionAction,
    FileConflictPolicy,
    resolve_output_path,
)


def test_missing_output_is_used(tmp_path: Path) -> None:
    target = tmp_path / "page.png"
    action, output = resolve_output_path(target, FileConflictPolicy.CANCEL)
    assert action is CollisionAction.USE
    assert output == target


def test_existing_output_can_be_skipped(tmp_path: Path) -> None:
    target = tmp_path / "page.png"
    target.write_text("existing", "utf-8")
    action, output = resolve_output_path(target, FileConflictPolicy.SKIP)
    assert action is CollisionAction.SKIP
    assert output == target


def test_existing_output_can_be_auto_renamed(tmp_path: Path) -> None:
    target = tmp_path / "page.png"
    target.write_text("existing", "utf-8")
    action, output = resolve_output_path(target, FileConflictPolicy.AUTO_RENAME)
    assert action is CollisionAction.USE
    assert output == tmp_path / "page-1.png"


def test_batch_internal_collision_is_detected(tmp_path: Path) -> None:
    target = tmp_path / "page.png"
    action, output = resolve_output_path(
        target, FileConflictPolicy.AUTO_RENAME, {target}
    )
    assert action is CollisionAction.USE
    assert output == tmp_path / "page-1.png"
