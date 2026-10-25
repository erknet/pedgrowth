"""WHO R anthropometry with standing versus recumbent measurements at 24 months."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator
from pedgrowth.data.who2006 import WhoPlan

ROOT = Path(__file__).parent / "fixtures/who_r"
MANIFEST = json.loads((ROOT / "position_manifest.json").read_text())
AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.DAYS)


def test_position_and_24_month_boundary_against_official_who_r():
    inputs = ROOT / "position_inputs.csv"
    expected = ROOT / "position_expected.csv"
    assert hashlib.sha256(inputs.read_bytes()).hexdigest() == MANIFEST["input_sha256"]
    assert hashlib.sha256(expected.read_bytes()).hexdigest() == MANIFEST["expected_sha256"]
    with expected.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == MANIFEST["cases"] == 12
    calc = GrowthChartsCalculator(plan=WhoPlan())
    for row in rows:
        days = float(row["age_days"])
        height = float(row["lenhei_cm"])
        weight = float(row["weight_kg"])
        sex = row["sex"]
        measured_standing = row["measure"] == "H"
        kind = "hfa" if measured_standing else "lfa"
        actual = calc.zscore(
            indicator=kind,
            sex=sex,
            age=days,
            age_definition=AGE,
            measurement=height,
        )
        assert actual == pytest.approx(float(row["expected_length_height_z"]), abs=0.02)
        size_indicator = "wfh" if measured_standing else "wfl"
        actual_size = calc.zscore(
            indicator=size_indicator,
            sex=sex,
            age=days,
            age_definition=AGE,
            coordinate=height,
            measurement=weight,
        )
        assert actual_size == pytest.approx(float(row["expected_weight_for_size_z"]), abs=0.03)
