from __future__ import annotations

import pytest

from pdf_image_exporter.core.page_ranges import PageRangeError, parse_page_ranges


def test_all_pages() -> None:
    assert parse_page_ranges("all", 3) == [1, 2, 3]


def test_sparse_ranges_are_sorted_and_deduplicated() -> None:
    assert parse_page_ranges("3,1,2-4", 5) == [1, 2, 3, 4]


def test_odd_even() -> None:
    assert parse_page_ranges("odd", 5) == [1, 3, 5]
    assert parse_page_ranges("even", 5) == [2, 4]


def test_out_of_range_is_rejected() -> None:
    with pytest.raises(PageRangeError):
        parse_page_ranges("1-4", 3)
