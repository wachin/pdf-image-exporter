"""Conversion planning models independent from the GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .conflicts import CollisionAction, FileConflictPolicy, resolve_output_path
from .conversion import ConversionSettings
from .naming import NamingContext, build_output_path
from .page_ranges import parse_page_ranges
from .pdf_info import PdfDocumentInfo


class JobStatus(str, Enum):
    """Lifecycle states for a document conversion job."""

    PENDING = "pending"
    READY = "ready"
    CONVERTING = "converting"
    PAUSED = "paused"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    CANCELED = "canceled"
    FAILED = "failed"


@dataclass(frozen=True)
class PlannedPage:
    """A single output page planned before process execution."""

    pdf_path: Path
    page: int
    output_path: Path
    width: int
    height: int

    @property
    def output_prefix(self) -> Path:
        return self.output_path.with_suffix("")

    @property
    def pixel_count(self) -> int:
        return self.width * self.height

    @property
    def estimated_memory_bytes(self) -> int:
        return self.pixel_count * 4


@dataclass
class ConversionJob:
    """A document-level conversion job."""

    info: PdfDocumentInfo
    settings: ConversionSettings
    pages: list[PlannedPage]
    status: JobStatus = JobStatus.PENDING
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class QueueSettings:
    """Runtime queue settings for future execution layers."""

    max_parallel_processes: int = 1
    stop_after_current: bool = False

    def validate(self) -> None:
        if self.max_parallel_processes < 1:
            raise ValueError("At least one process must be allowed.")
        if self.max_parallel_processes > 4:
            raise ValueError("The initial queue limits parallel processes to 4.")


@dataclass(frozen=True)
class ConversionPlan:
    """A batch conversion plan ready to be passed to an execution service."""

    jobs: tuple[ConversionJob, ...]
    skipped_outputs: tuple[Path, ...] = ()

    @property
    def pages(self) -> tuple[PlannedPage, ...]:
        return tuple(page for job in self.jobs for page in job.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def estimated_memory_bytes(self) -> int:
        return sum(page.estimated_memory_bytes for page in self.pages)

    @property
    def max_page_memory_bytes(self) -> int:
        return max((page.estimated_memory_bytes for page in self.pages), default=0)

    def resource_warning(self) -> str | None:
        """Return a warning when the plan may consume substantial resources."""

        total_mib = self.estimated_memory_bytes / (1024 * 1024)
        max_mib = self.max_page_memory_bytes / (1024 * 1024)
        if max_mib >= 512:
            return (
                f"A single page may require about {max_mib:.0f} MiB while "
                "rasterizing. This can be slow or memory intensive."
            )
        if total_mib >= 2048:
            return (
                f"The planned batch represents about {total_mib:.0f} MiB of "
                "uncompressed image data. Processing may take a while."
            )
        return None


def plan_conversions(
    documents: list[PdfDocumentInfo],
    settings: ConversionSettings,
    conflict_policy: FileConflictPolicy = FileConflictPolicy.CANCEL,
) -> ConversionPlan:
    """Build a conversion plan and resolve output-name collisions."""

    settings.validate()
    if settings.output_dir is None:
        raise ValueError("An output directory is required.")

    jobs: list[ConversionJob] = []
    skipped: list[Path] = []
    planned_paths: set[Path] = set()

    for info in documents:
        pages = parse_page_ranges(settings.page_expression, info.pages)
        planned_pages: list[PlannedPage] = []
        for page in pages:
            page_size = info.primary_page_size
            width = height = 0
            if page_size is not None:
                width, height = page_size.pixels_at(settings.dpi)
            desired = build_output_path(
                settings.output_dir,
                settings.name_template,
                NamingContext(
                    document=info.path.stem,
                    page=page,
                    pages=info.pages,
                    output_format=settings.output_format,
                    width=width,
                    height=height,
                    dpi=settings.dpi,
                ),
                settings.page_digits,
            )
            action, output_path = resolve_output_path(
                desired, conflict_policy, planned_paths
            )
            if action is CollisionAction.CANCEL:
                raise FileExistsError(f"Output already exists: {desired}")
            if action is CollisionAction.SKIP:
                skipped.append(desired)
                continue
            planned_paths.add(output_path)
            planned_pages.append(
                PlannedPage(
                    pdf_path=info.path,
                    page=page,
                    output_path=output_path,
                    width=width,
                    height=height,
                )
            )
        jobs.append(
            ConversionJob(
                info=info,
                settings=settings,
                pages=planned_pages,
                status=JobStatus.READY,
            )
        )
    return ConversionPlan(jobs=tuple(jobs), skipped_outputs=tuple(skipped))
