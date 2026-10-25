"""Clinically meaningful anthropometry examples without patient-identifiable data.

Published CDC examples are assessed against their reported z-score/percentile
or category; other plausible measurements are independently scored in WHO
anthro/anthroplus or CDC cdcanthro R, not computed by GrowthCharts fixtures.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import NormalDist

import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator
from pedgrowth.data.cdc import CdcClinicalPlan, CdcPlan
from pedgrowth.data.who2006 import WhoPlan
from pedgrowth.policies import InterpolationPolicy

FIX = Path(__file__).parent / "fixtures"
META = json.loads((FIX / "clinical_cases_manifest.json").read_text())


def clinical_rows() -> list[dict[str, str]]:
    left = FIX / "clinical_cases_input.csv"
    right = FIX / "clinical_cases_expected.csv"
    assert hashlib.sha256(left.read_bytes()).hexdigest() == META["original_inputs_sha256"]
    assert hashlib.sha256(right.read_bytes()).hexdigest() == META["expected_results_sha256"]
    with left.open(newline="", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))
    with right.open(newline="", encoding="utf-8") as f:
        scored = list(csv.DictReader(f))
    assert len(cases) == len(scored) == META["cases"] >= 40
    for left_case, right_case in zip(cases, scored, strict=True):
        for field in left_case:
            if field in ("age", "measurement", "coordinate", "published_percentile") and left_case[field]:
                assert float(left_case[field]) == float(right_case[field]), (left_case["id"], field)
            else:
                assert left_case[field] == right_case[field], (left_case["id"], field)
    return scored


CASES = clinical_rows()


@pytest.mark.parametrize("case", CASES, ids=lambda row: row["id"])
def test_patient_like_anthropometric_measurement_against_independent_sources(case):
    indicator = case["indicator"]
    is_cdc = case["reference"] == "cdc"
    # Half-month CDC inputs are exact knots, no interpolation ambiguity.
    calculator = GrowthChartsCalculator(
        plan=CdcPlan() if is_cdc else WhoPlan(),
        interpolation=InterpolationPolicy.LINEAR if is_cdc else InterpolationPolicy.NEAREST,
    )
    age_definition = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit(case["age_unit"]))
    result = calculator.calculate(
        indicator=indicator,
        sex=case["sex"],
        age=float(case["age"]),
        age_definition=age_definition,
        measurement=float(case["measurement"]),
        coordinate=float(case["coordinate"]) if case["coordinate"] else None,
    )
    family = "cdc" if is_cdc else "who2007" if case["reference"] == "who2007" else "who_"
    assert result.reference_id.startswith(family)
    expected = case["expected_z"]
    if case["source"] == "R_SYNTHETIC":
        assert expected, "Every synthetic case must have an official R expected z-score"
        tolerance = 0.020 if not is_cdc else 0.002
        assert result.zscore == pytest.approx(float(expected), abs=tolerance)
    elif case["id"] == "cdc-9mo-weight":
        # CDC's explicit worked example: 9-month male, 9.7 kg, z = 0.207.
        assert result.zscore == pytest.approx(0.207, abs=0.002)
        assert NormalDist().cdf(result.zscore) * 100 == pytest.approx(58, abs=0.6)
    elif case["id"] == "cdc-sam-bmi":
        assert NormalDist().cdf(result.zscore) * 100 == pytest.approx(28, abs=0.6)
    elif case["id"] == "cdc-olivia-extended-bmi":
        assert NormalDist().cdf(result.zscore) * 100 == pytest.approx(99.2, abs=0.15)
    elif case["id"].startswith("cdc-two-year-weight"):
        percentile = NormalDist().cdf(result.zscore) * 100
        if is_cdc:
            # CDC: 25th-50th according to the published transition example.
            assert 25 < percentile < 50
        else:
            # WHO: around 50th percentile.
            assert 45 < percentile < 55
    else:
        raise AssertionError("New published case needs an explicit expected metric")


def test_cdc_published_cases_use_independent_bmi_from_measured_height_weight():
    sam_bmi = 16.9 / (1.054**2)
    assert sam_bmi == pytest.approx(15.2, abs=0.02)
    # Published Olivia example: 175 pounds and 60 inches, BMI rounded to 34.2.
    olive_bmi = (175 * 0.45359237) / ((60 * 0.0254) ** 2)
    assert olive_bmi == pytest.approx(34.2, abs=0.04)


def test_clinical_transition_does_not_silently_select_the_wrong_source():
    age = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)
    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
    for months, source in ((23.999, "who"), (24.0, "cdc"), (24.001, "cdc")):
        result = calc.calculate(
            indicator="wfa",
            sex="M",
            age=months,
            age_definition=age,
            measurement=12.1335959,
        )
        assert result.reference_id.startswith(source)
