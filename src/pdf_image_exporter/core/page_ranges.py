"""Page range parsing and validation."""

from __future__ import annotations


class PageRangeError(ValueError):
    """Raised when a page range expression is invalid."""


def parse_page_ranges(expression: str, total_pages: int) -> list[int]:
    """Parse expressions such as ``1,3,5-9`` into sorted page numbers."""

    if total_pages < 1:
        raise PageRangeError("The document has no pages.")

    text = expression.strip().lower()
    if text in {"", "all"}:
        return list(range(1, total_pages + 1))
    if text in {"first"}:
        return [1]
    if text in {"odd", "odds"}:
        return [page for page in range(1, total_pages + 1) if page % 2 == 1]
    if text in {"even", "evens"}:
        return [page for page in range(1, total_pages + 1) if page % 2 == 0]

    pages: set[int] = set()
    for part in text.split(","):
        token = part.strip()
        if not token:
            raise PageRangeError("Empty page range component.")
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start = _parse_page_number(start_text)
            end = _parse_page_number(end_text)
            if start > end:
                raise PageRangeError("Page ranges must be ascending.")
            pages.update(range(start, end + 1))
        else:
            pages.add(_parse_page_number(token))

    invalid = [page for page in pages if page < 1 or page > total_pages]
    if invalid:
        raise PageRangeError(
            f"Page {invalid[0]} does not exist. The document has {total_pages} pages."
        )
    return sorted(pages)


def _parse_page_number(value: str) -> int:
    try:
        page = int(value)
    except ValueError as exc:
        raise PageRangeError(f"Invalid page number: {value}") from exc
    if page < 1:
        raise PageRangeError("Page numbers start at 1.")
    return page
