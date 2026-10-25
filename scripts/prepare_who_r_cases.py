"""Deterministic inputs for independent WHO R calculations; not expected outputs."""

import csv
from collections.abc import Callable
from pathlib import Path
from typing import cast

from pedgrowth.tables import Sex
from pedgrowth.tables.table import GrowthTable

from tests.reference_sets import WHO_TABLES

DEST = Path("tests/fixtures/who_r")
DEST.mkdir(parents=True, exist_ok=True)
with (DEST / "inputs.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["table", "indicator", "sex", "coordinate", "measurement"])
    for cls in WHO_TABLES:
        table = cast(Callable[[], GrowthTable], cls)()
        kind = table.get_table_type().value
        sex = table.get_table_sex()
        if sex not in (Sex.Male, Sex.Female):
            raise ValueError("WHO validation table must specify sex")
        indexes = sorted(table._indices[None])
        # Native reference-grid coordinates: lower, interior, upper; exclude
        # endpoints that the official WHO R package does not support.
        candidates = [
            indexes[1],
            indexes[len(indexes) // 4],
            indexes[len(indexes) // 2],
            indexes[3 * len(indexes) // 4],
            indexes[-2],
        ]
        for x in candidates:
            lms = table.get_lms(x, sex)
            for z in (-2, -1, 0, 1, 2):
                y = table.calculate_sd(lms, z)
                if y > 0:
                    w.writerow([table.get_file_name(), kind, sex.value, format(x, ".12g"), format(y, ".12g")])
print("Wrote independent R oracle inputs")
