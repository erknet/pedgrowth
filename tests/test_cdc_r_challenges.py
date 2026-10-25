"""Frozen independent CDC cdcanthro R outputs, including the extended-BMI tail."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import pytest
from pedgrowth import Sex
from pedgrowth.data.cdc.tables import CdcBmiForAge
from pedgrowth.tables.math import extended_bmi_z

ROOT = Path(__file__).parent / "fixtures/official_percentiles"
MANIFEST = json.loads((ROOT / "cdc_r_bmi_manifest.json").read_text())


def cases():
    left = ROOT / "cdc_r_bmi_inputs.csv"
    right = ROOT / "cdc_r_bmi_expected.csv"
    assert hashlib.sha256(left.read_bytes()).hexdigest() == MANIFEST["input_sha256"]
    assert hashlib.sha256(right.read_bytes()).hexdigest() == MANIFEST["expected_sha256"]
    with left.open(newline="") as f:
        input_rows = list(csv.DictReader(f))
    with right.open(newline="") as f:
        expected_rows = list(csv.DictReader(f))
    assert len(input_rows) == len(expected_rows) == MANIFEST["cases"]
    for inputs, expected in zip(input_rows, expected_rows, strict=True):
        assert inputs["sex"] == expected["sex"]
        assert float(inputs["age"]) == float(expected["age"])
        assert float(inputs["bmi"]) == float(expected["bmi"])
        yield inputs, expected


def test_cdc_extended_bmi_independent_r_with_tail_precision_limit():
    table = CdcBmiForAge()
    checked = 0
    unavailable = 0
    precision_limited = 0
    for inputs, expected in cases():
        age = float(inputs["age"])
        bmi = float(inputs["bmi"])
        if not expected["expected"]:
            # cdcanthro does not provide output at age 240 months and older.
            assert age >= 240
            unavailable += 1
            continue
        sex = Sex.Male if inputs["sex"] == "1" else Sex.Female
        actual = table.calculate_zscore(age, bmi, sex)
        target = float(expected["expected"])
        if target >= 8.20:
            # cdcanthro saturates at ~8.21 where floating-point 1-p rounds to 1.
            # The corrected Python path retains more tail precision; compare
            # to the stable SciPy normal inverse in a separate test.
            assert actual >= 8.20
            precision_limited += 1
        else:
            assert actual == pytest.approx(target, abs=0.025), (inputs, actual, target)
        checked += 1
    assert checked == MANIFEST["official_available"]
    assert unavailable == MANIFEST["official_unavailable"]
    assert precision_limited > 0


@pytest.mark.parametrize("excess", [0.0, 2.0, 5.0, 6.0, 7.0, 8.0, 12.0, 20.0, 40.0])
def test_extended_bmi_survival_tail_against_scipy(excess):
    scipy_special = pytest.importorskip("scipy.special")
    expected = -scipy_special.ndtri_exp(math.log(0.1) + scipy_special.log_ndtr(-excess))
    assert extended_bmi_z(excess) == pytest.approx(expected, abs=3e-8)
