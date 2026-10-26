"""Fixed-seed INTERGROWTH scenarios independent of Python reference equations."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "output", nargs="?", type=Path, default=ROOT / "tests/fixtures/intergrowth/continuous_inputs.csv"
)
OUTPUT = parser.parse_args().output

FAMILIES: tuple[tuple[str, str, float, float, float, float], ...] = (
    ("preterm_postnatal", "weight", 27, 64, 0.45, 10),
    ("preterm_postnatal", "length", 27, 64, 25, 83),
    ("preterm_postnatal", "head_circumference", 27, 64, 18, 55),
    ("preterm_postnatal", "weight_for_length", 35, 65, 0.35, 10),
    ("very_preterm_birth", "weight", 168, 230, 0.25, 3.2),
    ("very_preterm_birth", "length", 168, 230, 23, 51),
    ("very_preterm_birth", "head_circumference", 168, 230, 18, 38),
)

rng = random.Random(20261017)  # noqa: S311  # Reproducible non-security test data.
rows = []
for family, indicator, minimum, maximum, low, high in FAMILIES:
    for sex in ("M", "F"):
        # The coordinates/measurements are independent fixture inputs; no
        # GrowthCharts LMS coefficients or functions produce expected scores.
        knots = [
            minimum,
            minimum + 0.000001,
            minimum + (maximum - minimum) * 0.01,
            minimum + (maximum - minimum) / 8,
            minimum + (maximum - minimum) / 4,
            (minimum + maximum) / 2,
            maximum - (maximum - minimum) / 4,
            maximum - (maximum - minimum) / 8,
            maximum - (maximum - minimum) * 0.01,
            maximum - 0.000001,
            maximum,
        ]
        for x in knots:
            for ratio in (0.55, 0.8, 1.0, 1.2, 1.55):
                y = (low + (high - low) * ((x - minimum) / (maximum - minimum))) * ratio
                rows.append((family, indicator, sex, f"{x:.15g}", f"{y:.15g}", "boundary"))
        for i in range(300):
            x = rng.uniform(minimum, maximum)
            # A mixture of plausible and deliberately extreme measurements.
            t = rng.random()
            y = (low + (high - low) * ((x - minimum) / (maximum - minimum))) * (
                rng.uniform(0.48, 1.67) if i % 6 else rng.uniform(0.08, 2.75)
            )
            rows.append((family, indicator, sex, f"{x:.15g}", f"{y:.15g}", "random" if i % 6 else "extreme"))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("w", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow(("family", "indicator", "sex", "coordinate", "measurement", "scenario"))
    writer.writerows(rows)
print(f"Wrote {len(rows)} reproducible INTERGROWTH challenge inputs")
