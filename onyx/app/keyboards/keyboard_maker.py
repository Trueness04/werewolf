"""Generic keyboard builder (stub)."""

from __future__ import annotations

from typing import Any


def build_inline(rows: list[list[dict[str, Any]]]) -> Any:
    """Build an inline keyboard from row data."""
    return rows


def build_reply(rows: list[list[str]]) -> Any:
    """Build a reply keyboard from row data."""
    return rows
