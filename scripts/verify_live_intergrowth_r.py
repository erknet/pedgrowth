"""Compare published INTERGROWTH Python equations with live independent gigs R.

The input is a CSV emitted by export_intergrowth_gigs_r.R after verifying the
exact original gigs 0.5.2 source hashes. Measurements are synthetic challenges;
neither expected outcomes nor fitted coefficients are bundled in the repository.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from pedgrowth.data.intergrowth.intergrowth import (
    IntergrowthCalculator,
    IntergrowthIndicator,
    IntergrowthReference,
)

FAMILIES = {
    "preterm_postnatal": {"weight", "length", "head_circumference", "weight_for_length"},
    "very_preterm_birth": {"weight", "length", "head_circumference"},
}


def validate(path: Path, *, tolerance: float = 5e-11) -> tuple[int, float]:
    calculators = {family: IntergrowthCalculator(IntergrowthReference(family)) for family in FAMILIES}
    seen: set[tuple[str, str, str]] = set()
    count = 0
    worst = 0.0
    with path.open(newline="", encoding="utf-8") as stream:
        rows = csv.DictReader(stream)
        required = {"family", "indicator", "sex", "coordinate", "measurement", "scenario", "expected"}
        if rows.fieldnames is None or not required.issubset(rows.fieldnames):
            raise ValueError("Unexpected independent gigs reference schema")
        for row in rows:
            family = row["family"]
            indicator = row["indicator"]
            sex = row["sex"]
            if family not in FAMILIES or indicator not in FAMILIES[family] or sex not in {"M", "F"}:
                raise ValueError("Unexpected INTERGROWTH reference family, indicator or sex")
            seen.add((family, indicator, sex))
            actual = calculators[family].zscore(
                IntergrowthIndicator(indicator),
                float(row["measurement"]),
                float(row["coordinate"]),
                sex,
            )
            expected = float(row["expected"])
            if not (math.isfinite(actual) and math.isfinite(expected)):
                raise AssertionError("Non-finite independent INTERGROWTH result")
            error = abs(actual - expected)
            worst = max(worst, error)
            if error > tolerance:
                raise AssertionError(
                    f"INTERGROWTH R/Python disagreement at row {count}: "
                    f"{family}/{indicator}/{sex} observed {actual} versus {expected}"
                )
            count += 1
    expected_cases = {
        (family, indicator, sex)
        for family, indicators in FAMILIES.items()
        for indicator in indicators
        for sex in ("M", "F")
    }
    if seen != expected_cases or count < 4900:
        raise AssertionError(
            f"Missing independent INTERGROWTH challenge coverage: "
            f"{len(seen)}/{len(expected_cases)} groups; {count} observations"
        )
    return count, worst


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    count, worst = validate(args.results)
    print(f"PASS: {count} live R/Python INTERGROWTH comparisons; largest z-error={worst:.3g}")


if __name__ == "__main__":
    main()
