"""PDF dimension helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose

POINTS_PER_INCH = 72.0
MM_PER_INCH = 25.4


@dataclass(frozen=True)
class PageSize:
    """A page size in PDF points."""

    width_points: float
    height_points: float

    @property
    def width_inches(self) -> float:
        return self.width_points / POINTS_PER_INCH

    @property
    def height_inches(self) -> float:
        return self.height_points / POINTS_PER_INCH

    @property
    def width_mm(self) -> float:
        return self.width_inches * MM_PER_INCH

    @property
    def height_mm(self) -> float:
        return self.height_inches * MM_PER_INCH

    @property
    def orientation(self) -> str:
        if isclose(self.width_points, self.height_points, abs_tol=0.5):
            return "square"
        return "landscape" if self.width_points > self.height_points else "portrait"

    def pixels_at(self, dpi: int) -> tuple[int, int]:
        return (
            round(self.width_inches * dpi),
            round(self.height_inches * dpi),
        )


STANDARD_SIZES_MM: dict[str, tuple[float, float]] = {
    "A0": (841, 1189),
    "A1": (594, 841),
    "A2": (420, 594),
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "A6": (105, 148),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
    "Tabloid": (279.4, 431.8),
    "Ledger": (431.8, 279.4),
    "Executive": (184.15, 266.7),
    "B4": (250, 353),
    "B5": (176, 250),
}


def recognize_standard_size(size: PageSize, tolerance_mm: float = 2.0) -> str:
    """Return a common paper name or ``Custom`` for a page size."""

    actual = (size.width_mm, size.height_mm)
    swapped = (size.height_mm, size.width_mm)
    for name, expected in STANDARD_SIZES_MM.items():
        if _close_pair(actual, expected, tolerance_mm):
            return name
        if _close_pair(swapped, expected, tolerance_mm):
            return name
    return "Custom"


def _close_pair(
    actual: tuple[float, float], expected: tuple[float, float], tolerance_mm: float
) -> bool:
    return (
        abs(actual[0] - expected[0]) <= tolerance_mm
        and abs(actual[1] - expected[1]) <= tolerance_mm
    )
