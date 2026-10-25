"""Convert an official WHO XLSX or CDC CSV into a validated table override.

Example:
    python scripts/convert_reference.py --table who_weight_for_age_boys \
        --source official-wfa-boys.xlsx --output updated-wfa-boys.csv

Requires 'openpyxl' only when converting WHO XLSX files.
No network access; the source file must be downloaded separately.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pedgrowth.data.cdc.tables import CDC_TABLES
from pedgrowth.reference_data import CDC_BMI_FIELDS, CSV_FIELDS, check_dataset_shape, parse_lms_csv
from pedgrowth.tables.table import GrowthTable

from scripts.refresh_data import rows_for_table
from tests.reference_sets import WHO_TABLES


def _instantiate(factory: Callable[[], GrowthTable]) -> GrowthTable:
    return factory()


TABLES: dict[str, Callable[[], GrowthTable]] = {
    _instantiate(cls).get_file_name(): cls for cls in [*WHO_TABLES, *CDC_TABLES]
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", required=True, choices=sorted(TABLES))
    parser.add_argument("--source", required=True, type=Path, help="Local WHO XLSX or CDC CSV")
    parser.add_argument("--output", required=True, type=Path, help="Normalized override CSV")
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Source and output files must differ")
    if not args.source.is_file() or args.source.stat().st_size > 15_000_000:
        parser.error("Source file is missing or exceeds 15 MB")
    if args.output.exists():
        parser.error("Output file exists; choose a new filename")
    table = TABLES[args.table]()
    if args.table.startswith("who") and args.source.suffix.lower() != ".xlsx":
        parser.error("WHO source must be an XLSX workbook")
    if args.table.startswith("cdc_") and args.source.suffix.lower() != ".csv":
        parser.error("CDC source must be a CSV file")

    rows = rows_for_table(args.source.read_bytes(), TABLES[args.table])
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(CDC_BMI_FIELDS if args.table == "cdc_bmi_for_age" else CSV_FIELDS)
    writer.writerows(rows)
    normalized = output.getvalue()
    table_data = parse_lms_csv(io.StringIO(normalized, newline=""), args.table)
    check_dataset_shape(
        table_data,
        sex_specific=table.get_col_index_sex() is not None,
        extended_bmi=table.get_col_index_sigma() is not None,
        name=args.table,
    )
    result = normalized.encode("utf-8")
    if len(result) > 10_000_000:
        parser.error("Normalized file exceeds the 10 MB override limit")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f"Created: {args.output} ({len(rows)} rows)")
    print(f"SHA-256: {hashlib.sha256(result).hexdigest()}")


if __name__ == "__main__":
    main()
