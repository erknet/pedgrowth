"""Build deterministic inputs; WHO R, not GrowthCharts, produces their expected z-scores.

The bundled coefficients only choose physically-scaled challenge measurements.
The tests do not use those coefficients to compute expected values.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

from pedgrowth.policies import InterpolationPolicy
from pedgrowth.tables import Sex
from pedgrowth.tables.table import GrowthTable

from tests.reference_sets import WHO_TABLES

DEST = Path("tests/fixtures/who_r")
DEST.mkdir(parents=True, exist_ok=True)


def measurement_at(table: GrowthTable, x: float, sex: Sex, z: float, policy: InterpolationPolicy) -> float:
    lms = table.get_lms(x, sex, policy)
    if z > 3:
        sd3 = table.calculate_sd(lms, 3)
        sd2 = table.calculate_sd(lms, 2)
        return sd3 + (z - 3) * (sd3 - sd2)
    if z < -3:
        sd3 = table.calculate_sd(lms, -3)
        sd2 = table.calculate_sd(lms, -2)
        return sd3 - (-z - 3) * (sd2 - sd3)
    return table.calculate_sd(lms, z)


with (DEST / "challenges_input.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream)
    writer.writerow(("table", "indicator", "sex", "coordinate", "measurement", "interpolation", "target_z"))
    for table_class in WHO_TABLES:
        factory: Callable[[], GrowthTable] = table_class
        table = factory()
        sex = table.get_table_sex()
        if sex not in (Sex.Male, Sex.Female):
            raise ValueError("WHO table sex undefined")
        keys = table._indices[None]
        points = sorted(
            {
                0,
                1,
                2,
                len(keys) // 8,
                len(keys) // 4,
                len(keys) // 2,
                len(keys) * 3 // 4,
                len(keys) * 7 // 8,
                len(keys) - 3,
                len(keys) - 2,
                len(keys) - 1,
            }
        )
        for k in points:
            x = float(keys[k])
            for z in (-4.0, -3.5, -3.0, -2.5, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 3.5, 4.0):
                try:
                    measurement = measurement_at(table, x, sex, z, InterpolationPolicy.NEAREST)
                except (ValueError, OverflowError):
                    continue
                if measurement > 0:
                    writer.writerow(
                        (
                            table.get_file_name(),
                            table.get_table_type().value,
                            sex.value,
                            f"{x:.17g}",
                            f"{measurement:.12g}",
                            "nearest",
                            z,
                        )
                    )
        # Interior coordinates, not restricted to the reference grid.
        for k in (len(keys) // 5, len(keys) // 2, len(keys) * 4 // 5):
            if k + 1 >= len(keys):
                continue
            for fraction in (0.2, 0.73):
                x = keys[k] * (1 - fraction) + keys[k + 1] * fraction
                policy = (
                    InterpolationPolicy.NEAREST
                    if table.get_file_name().startswith("who_")
                    else InterpolationPolicy.LINEAR
                )
                for z in (-3, -1, 0, 1, 3):
                    try:
                        measurement = measurement_at(table, x, sex, z, policy)
                    except (ValueError, OverflowError):
                        continue
                    if measurement > 0:
                        writer.writerow(
                            (
                                table.get_file_name(),
                                table.get_table_type().value,
                                sex.value,
                                f"{x:.17g}",
                                f"{measurement:.12g}",
                                policy.value,
                                z,
                            )
                        )
print(f"Wrote {DEST / 'challenges_input.csv'}")
