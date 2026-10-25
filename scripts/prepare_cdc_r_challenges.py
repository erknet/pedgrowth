"""Generate CDC BMI challenge measurements from published CDC percentiles."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "tests/fixtures/official_percentiles/cdc_bmi_for_age.csv"
percentiles: dict[tuple[int, float], dict[str, float]] = defaultdict(dict)
with source.open(newline="", encoding="utf-8") as file:
    for row in csv.DictReader(file):
        percentiles[(int(row["sex"]), float(row["coordinate"]))][row["percentile"]] = float(
            row["measurement"]
        )
out = ROOT / "tests/fixtures/official_percentiles/cdc_r_bmi_inputs.csv"
with out.open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(("sex", "age", "bmi", "scenario"))
    for (sex, age), points in sorted(percentiles.items()):
        if age not in (24.0, 24.5, 30.5, 50.5, 51.0, 60.5, 100.5, 114.5, 180.5, 200.5, 238.5, 240.0):
            continue
        p95 = points["p95"]
        p50 = points["p50"]
        for scenario, value in (
            ("p50", p50),
            ("p95-epsilon", p95 - 0.001),
            ("p95", p95),
            ("p95+epsilon", p95 + 0.001),
            ("p95+3", p95 + 3.0),
            ("p95+10", p95 + 10.0),
            ("p95+18", p95 + 18.0),
            ("independent-fixed-15", 15.0),
            ("independent-fixed-35", 35.0),
        ):
            writer.writerow((sex, age, round(value, 7), scenario))
print(out)
