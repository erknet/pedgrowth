"""WHO 2007 reference acquisition adapter (no bundled coefficients)."""

from __future__ import annotations

from typing import Any, cast

from pedgrowth.acquisition import initialize_spreadsheet_provider, normalize_spreadsheet

from .tables import WHO_2007_TABLES

_normalize = normalize_spreadsheet

TABLE_CLASSES = {cast(Any, cls).__new__(cls).get_file_name(): cls for cls in WHO_2007_TABLES}


def initialize_data(filename: str | None = None) -> int:
    """Acquire only a requested table, or best-effort initialize all tables."""
    return initialize_spreadsheet_provider("who2007", TABLE_CLASSES, filename)
