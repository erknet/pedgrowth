"""Compare the Python calculator to independent WHO/CDC R-produced z-scores.

The input CSV must be exported by scripts/export_official.R, not by this
package. This is an opt-in external validation gate, distinct from tests that
compare a formula with itself or with historical pygrowup versions.

Usage:
    Rscript scripts/export_official.R /tmp/official-values.csv
    python scripts/validate_official.py /tmp/official-values.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pedgrowth import GrowthChartsCalculator


def compare(path: Path, tolerance: float = 0.03) -> tuple[int, float]:
    """Return number of independently checked cases and worst absolute error."""
    if not path.is_file():
        raise FileNotFoundError(path)
    calculators = {
        "who": GrowthChartsCalculator(standard="who", interpolation="linear"),
        "cdc": GrowthChartsCalculator(standard="cdc", interpolation="linear"),
    }
    count = 0
    largest = 0.0
    examples: list[str] = []
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        expected_columns = ["standard", "indicator", "age", "sex", "measurement", "expected"]
        if reader.fieldnames != expected_columns:
            raise ValueError("Unknown independent reference CSV schema")
        for row in reader:
            standard = row["standard"]
            if standard not in calculators:
                raise ValueError(f"Unknown reference standard {standard!r}")
            age = float(row["age"])
            measurement = float(row["measurement"])
            expected = float(row["expected"])
            if not all(math.isfinite(x) for x in (age, measurement, expected)):
                raise ValueError("Independent reference contains non-finite value")
            actual = calculators[standard].zscore_for_measurement(
                row["indicator"],
                measurement,
                row["sex"],
                age,
            )
            if actual is None:
                raise ValueError("Unexpected None z-score from calculator")
            difference = abs(actual - expected)
            largest = max(largest, difference)
            count += 1
            if difference > tolerance:
                examples.append(
                    f"{standard} {row['indicator']} {row['sex']} age={age}: "
                    f"actual={actual:.6f}, official={expected:.6f}, difference={difference:.6f}"
                )
    if count < 85:
        raise RuntimeError(f"Independent reference matrix unexpectedly small: {count}")
    if examples:
        raise AssertionError(
            f"{len(examples)}/{count} externally verified z-scores differ by more than {tolerance}:\n"
            + "\n".join(examples[:20])
        )
    return count, largest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--tolerance", type=float, default=0.03)
    args = parser.parse_args()
    if not 0 < args.tolerance <= 0.1:
        parser.error("Tolerance must be in (0, 0.1]")
    count, worst = compare(args.file, args.tolerance)
    print(f"PASS: {count} independent reference calculations; worst z-error={worst:.7f}")


if __name__ == "__main__":
    main()
