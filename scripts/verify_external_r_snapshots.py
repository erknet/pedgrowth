"""Compare new external R runs with frozen WHO/CDC numerical oracles.

Regenerate external results independently, then pass paths in this order:
WHO baseline, WHO challenges, CDC extended BMI. Do not regenerate inputs
from the library under test as part of the verification gate.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "tests/fixtures"


def check(
    frozen: Path,
    generated: Path,
    *,
    atol: float,
    expected_fields: tuple[str, ...] = ("expected",),
) -> tuple[int, int]:
    with frozen.open(newline="", encoding="utf-8") as f:
        recorded = list(csv.DictReader(f))
    with generated.open(newline="", encoding="utf-8") as f:
        fresh = list(csv.DictReader(f))
    if not recorded or len(recorded) != len(fresh):
        raise AssertionError(f"R oracle size changed: {frozen.name} {len(recorded)} vs {len(fresh)}")
    verified = 0
    missing = 0
    for index, (old, new) in enumerate(zip(recorded, fresh, strict=True)):
        for field in (
            "table",
            "family",
            "indicator",
            "sex",
            "interpolation",
            "scenario",
            "id",
            "source",
            "reference",
            "age_unit",
            "measured_position",
        ):
            if field in old and old[field] != new[field]:
                raise AssertionError(f"R oracle identity changed: {frozen.name}:{index}:{field}")
        for field in ("coordinate", "measurement", "age", "published_percentile"):
            if field in old and bool(old[field]) != bool(new[field]):
                raise AssertionError(f"R oracle input missingness changed: {frozen.name}:{index}:{field}")
            if (
                field in old
                and old[field]
                and (not math.isclose(float(old[field]), float(new[field]), rel_tol=0, abs_tol=1e-9))
            ):
                raise AssertionError(f"R oracle input changed: {frozen.name}:{index}:{field}")
        for expected_key in expected_fields:
            if not old[expected_key] or not new[expected_key]:
                if old[expected_key] != new[expected_key]:
                    raise AssertionError(f"R oracle availability changed: {frozen.name}:{index}")
                missing += 1
                continue
            a, b = float(old[expected_key]), float(new[expected_key])
            if not math.isfinite(a) or not math.isfinite(b) or abs(a - b) > atol:
                raise AssertionError(f"R oracle discrepancy: {frozen.name}:{index} {a} versus {b}")
            verified += 1
    return verified, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("who_baseline", type=Path)
    parser.add_argument("who_challenges", type=Path)
    parser.add_argument("cdc_bmi", type=Path)
    parser.add_argument("who_positions", type=Path)
    parser.add_argument("--intergrowth", type=Path)
    parser.add_argument("--clinical", type=Path)
    args = parser.parse_args()
    fixture_pairs: list[tuple[Path, Path]] = [
        (ROOT / "who_r/expected.csv", args.who_baseline),
        (ROOT / "who_r/challenges_expected.csv", args.who_challenges),
        (ROOT / "official_percentiles/cdc_r_bmi_expected.csv", args.cdc_bmi),
        (ROOT / "who_r/position_expected.csv", args.who_positions),
    ]
    if args.intergrowth is not None:
        fixture_pairs.append((ROOT / "intergrowth/continuous_expected.csv", args.intergrowth))
    if args.clinical is not None:
        fixture_pairs.append((ROOT / "clinical_cases_expected.csv", args.clinical))
    for frozen, generated in fixture_pairs:
        fields = (
            ("expected_length_height_z", "expected_weight_for_size_z")
            if frozen.name == "position_expected.csv"
            else ("expected_z",)
            if frozen.name == "clinical_cases_expected.csv"
            else ("expected",)
        )
        atol = 5e-11 if frozen.name == "continuous_expected.csv" else 0.02
        checked, absent = check(frozen, generated, atol=atol, expected_fields=fields)
        print(f"Verified {frozen.name}: {checked} independent R outputs; {absent} explicitly unavailable")


if __name__ == "__main__":
    main()
