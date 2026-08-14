"""Pagination helpers."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def paginate(items: list[T], page_size: int) -> list[list[T]]:
    """Return chunks of items of length at most page_size."""
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    return [items[start : start + page_size] for start in range(0, len(items), page_size)]
