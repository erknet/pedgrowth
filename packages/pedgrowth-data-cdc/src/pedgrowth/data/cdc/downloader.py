"""Verified, on-demand acquisition of official CDC reference CSVs.

The extension never bundles the numeric coefficients. CDC source content is
downloaded directly, pinned to an audited SHA-256 and converted to the
portable, immutable LMSB cache by the generic provider loader.
"""

from __future__ import annotations

import csv
import io
from typing import Any, cast

from pedgrowth.acquisition import initialize_reference_provider
from pedgrowth.exceptions import DataError
from pedgrowth.reference_data import CDC_BMI_FIELDS, CSV_FIELDS
from pedgrowth.tables import Sex
from pedgrowth.tables.table import GrowthTable

from .tables import CDC_TABLES

TABLE_CLASSES: dict[str, type[GrowthTable]] = {
    cast(Any, cls).__new__(cls).get_file_name(): cast(type[GrowthTable], cls) for cls in CDC_TABLES
}


def normalize_source(source: bytes, table_class: type[GrowthTable]) -> bytes:
    """Normalize a CDC CSV without changing its substantive LMS/sigma values."""
    table = cast(Any, table_class).__new__(table_class)
    name = table.get_file_name()
    extended_bmi = table.get_col_index_sigma() is not None
    try:
        reader = csv.reader(io.StringIO(source.decode("utf-8-sig")))
        header = next(reader, None)
        if not header or header[0].strip().lower() != "sex":
            raise DataError(f"Unexpected CDC source header in {name!r}: {header}")
        result = io.StringIO(newline="")
        writer = csv.writer(result, lineterminator="\n")
        writer.writerow(CDC_BMI_FIELDS if extended_bmi else CSV_FIELDS)
        count = 0
        for line, row in enumerate(reader, start=2):
            if not row or not any(value.strip() for value in row):
                continue
            if row[0].strip().lower() == "sex":
                continue  # Official CSVs can repeat their header between sex groups.
            try:
                code = int(row[0])
                if code not in (1, 2):
                    raise ValueError("Unknown CDC sex code")
                index = float(row[table.get_col_index_measurement()])
                l = float(row[table.get_col_index_l()])
                m = float(row[table.get_col_index_m()])
                s = float(row[table.get_col_index_s()])
                sigma_column = table.get_col_index_sigma()
                sigma = float(row[sigma_column]) if sigma_column is not None else None
                p95 = float(row[14]) if extended_bmi else None
            except (ValueError, TypeError, IndexError) as exc:
                raise DataError(f"Invalid CDC scientific coefficient at {name}:{line}") from exc
            values = [
                Sex.Male.value if code == 1 else Sex.Female.value,
                repr(index),
                repr(l),
                repr(m),
                repr(s),
                repr(sigma) if sigma is not None else "",
            ]
            if p95 is not None:
                values.append(repr(p95))
            writer.writerow(values)
            count += 1
        if count < 30:
            raise DataError(f"Unexpectedly short CDC reference CSV: {name}")
        return result.getvalue().encode("utf-8")
    except UnicodeError as exc:
        raise DataError(f"Invalid CDC source encoding for {name}") from exc


def initialize_data(filename: str | None = None) -> int:
    """Acquire only a requested table, or try every missing CDC table."""
    return initialize_reference_provider("cdc", TABLE_CLASSES, normalize_source, filename)
