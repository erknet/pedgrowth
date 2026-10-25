"""Strict, data-only CSV parsing for bundled and user-selected LMS references.

The loader never evaluates Python expressions or deserializes objects.
Files must already be normalized to: sex,index,l,m,s,sigma.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
from collections.abc import Mapping
from pathlib import Path
from typing import IO

from .exceptions import DataError
from .tables.lms import LMS
from .tables.sex import Sex

CSV_FIELDS = ["sex", "index", "l", "m", "s", "sigma"]
CDC_BMI_FIELDS = [*CSV_FIELDS, "p95"]
MAX_OVERRIDE_BYTES = 10_000_000
MAX_TABLE_ROWS = 100_000


def parse_lms_csv(stream: IO[str], name: str) -> dict[Sex | None, dict[float, LMS]]:
    """Parse numeric coefficients with strict schema and finite-value checks."""
    table: dict[Sex | None, dict[float, LMS]] = {}
    try:
        reader = csv.DictReader(stream)
        valid_fields = CDC_BMI_FIELDS
        if reader.fieldnames not in (CSV_FIELDS, CDC_BMI_FIELDS):
            raise DataError(f"Invalid CSV columns in {name!r}; expected: {','.join(valid_fields)}")
        for count, row in enumerate(reader, start=1):
            if count > MAX_TABLE_ROWS:
                raise DataError(f"Reference table {name!r} exceeds the row limit")
            if None in row or any(value is None for value in row.values()):
                raise DataError(f"Malformed CSV row {count} in {name!r}")
            sex = Sex(row["sex"]) if row["sex"] else None
            idx = float(row["index"])
            lms = LMS(
                l=float(row["l"]),
                m=float(row["m"]),
                s=float(row["s"]),
                sigma=float(row["sigma"]) if row["sigma"] else None,
                p95=float(row["p95"]) if row.get("p95") else None,
            )
            if not math.isfinite(idx) or idx < 0:
                raise DataError(f"Invalid reference index in {name!r}, row {count}")
            values = (lms.l, lms.m, lms.s)
            if not all(math.isfinite(n) for n in values) or lms.m <= 0 or lms.s <= 0:
                raise DataError(f"Invalid LMS parameters in {name!r}, row {count}")
            if lms.sigma is not None and (not math.isfinite(lms.sigma) or lms.sigma <= 0):
                raise DataError(f"Invalid sigma in {name!r}, row {count}")
            if lms.p95 is not None and (not math.isfinite(lms.p95) or lms.p95 <= lms.m):
                raise DataError(f"Invalid published P95 in {name!r}, row {count}")
            bucket = table.setdefault(sex, {})
            if idx in bucket:
                raise DataError(f"Duplicate reference index {idx} in {name!r}")
            bucket[idx] = lms
    except (csv.Error, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise DataError(f"Invalid reference CSV {name!r}: {exc}") from exc
    if not table:
        raise DataError(f"Empty reference table: {name!r}")
    return table


def read_override_csv(path: str | Path) -> tuple[dict[Sex | None, dict[float, LMS]], str]:
    """Read a bounded CSV without execution; return rows and content SHA-256."""
    if not isinstance(path, (str, Path)):
        raise DataError("Override path must be a string or pathlib.Path")
    source = Path(path).expanduser()
    try:
        if not source.is_file():
            raise DataError(f"Reference override is not a regular file: {source}")
        if source.stat().st_size > MAX_OVERRIDE_BYTES:
            raise DataError(f"Reference override exceeds {MAX_OVERRIDE_BYTES} bytes: {source}")
        data = source.read_bytes()
        if len(data) > MAX_OVERRIDE_BYTES:
            raise DataError(f"Reference override exceeds {MAX_OVERRIDE_BYTES} bytes: {source}")
        stream = io.StringIO(data.decode("utf-8-sig"), newline="")
        return parse_lms_csv(stream, str(source)), hashlib.sha256(data).hexdigest()
    except (OSError, UnicodeError) as exc:
        raise DataError(f"Cannot read reference override {source}: {exc}") from exc


def check_dataset_shape(
    table: Mapping[Sex | None, Mapping[float, LMS]],
    *,
    sex_specific: bool,
    extended_bmi: bool,
    name: str,
) -> None:
    """Avoid malformed or partial sex partitions and missing BMI sigma."""
    sexes = set(table)
    expected = {Sex.Male, Sex.Female} if sex_specific else {None}
    if sexes != expected:
        raise DataError(f"Reference {name!r} requires sex partitions {expected}, got {sexes}")
    if sex_specific and set(table[Sex.Male]) != set(table[Sex.Female]):
        raise DataError(f"Reference {name!r} must have the same indices for both sexes")
    for observations in table.values():
        for lms in observations.values():
            if extended_bmi and (lms.sigma is None or lms.p95 is None):
                raise DataError(f"Reference {name!r} requires sigma and P95 for every observation")
            if not extended_bmi and (lms.sigma is not None or lms.p95 is not None):
                raise DataError(f"Reference {name!r} should not contain sigma or P95")
