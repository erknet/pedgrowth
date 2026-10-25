"""Independent numerical oracles exercised through the NumPy execution engine."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator
from pedgrowth.data.cdc.tables import CDC_TABLES
from pedgrowth.data.intergrowth.intergrowth_tables import (
    INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthWeightForAge,
)
from pedgrowth.tables import AGE_BASED_TYPES

from tests.reference_sets import WHO_TABLES

ROOT = Path(__file__).parent / "fixtures"
AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)
PERCENTILES = {"p3": 0.03, "p5": 0.05, "p50": 0.5, "p95": 0.95}


@pytest.mark.parametrize("table_class", WHO_TABLES, ids=lambda cls: cls.__name__)
def test_typed_batch_vs_who_r_each_table(table_class):
    table = table_class()
    calc = GrowthChartsCalculator(table=table)
    name = table.get_file_name()
    with (ROOT / "who_r/challenges_input.csv").open(newline="") as stream:
        inputs = [row for row in csv.DictReader(stream) if row["table"] == name]
    with (ROOT / "who_r/challenges_expected.csv").open(newline="") as stream:
        official = [row for row in csv.DictReader(stream) if row["table"] == name]
    samples = [
        (x, y)
        for x, y in zip(inputs, official, strict=True)
        if y["expected"] and x["interpolation"] == "nearest"
    ][::7]
    assert len(samples) >= 10
    xs = [float(x["coordinate"]) for x, _ in samples]
    ys = [float(x["measurement"]) for x, _ in samples]
    sex = table.get_table_sex()
    assert sex is not None
    arguments = (
        {"ages": xs, "age_definition": AGE}
        if table.get_table_type() in AGE_BASED_TYPES
        else {"coordinates": xs}
    )
    scores, references = calc.calculate_numpy(
        indicator=table.get_table_type().value,
        sexes=sex.value,
        measurements=ys,
        **arguments,
    )
    assert np.isfinite(scores).all()
    assert all(ref == name for ref in references)
    for score, (_, expected) in zip(scores, samples, strict=True):
        assert score == pytest.approx(float(expected["expected"]), abs=0.025)


@pytest.mark.parametrize("table_class", CDC_TABLES, ids=lambda cls: cls.__name__)
def test_typed_batch_vs_published_cdc_percentiles_each_table(table_class):
    table = table_class()
    calc = GrowthChartsCalculator(table=table)
    name = table.get_file_name()
    with (ROOT / "official_percentiles" / f"{name}.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))[::29]
    assert len(rows) >= 5
    xs = [float(row["coordinate"]) for row in rows]
    measurements = [float(row["measurement"]) for row in rows]
    sexes = ["M" if row["sex"] == "1" else "F" for row in rows]
    arguments = (
        {"ages": xs, "age_definition": AGE}
        if table.get_table_type() in AGE_BASED_TYPES
        else {"coordinates": xs}
    )
    scores, references = calc.calculate_numpy(
        indicator=table.get_table_type().value,
        measurements=measurements,
        sexes=sexes,
        **arguments,
    )
    assert all(ref == name for ref in references)
    for score, row in zip(scores, rows, strict=True):
        expected = NormalDist().inv_cdf(PERCENTILES[row["percentile"]])
        assert math.isfinite(score)
        assert score == pytest.approx(expected, abs=0.035)


INTERGROWTH = (
    *INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthWeightForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
)


@pytest.mark.parametrize("table_class", INTERGROWTH, ids=lambda cls: cls.__name__)
def test_typed_batch_vs_published_intergrowth_each_table(table_class):
    table = table_class()
    calc = GrowthChartsCalculator(table=table)
    family = "ig_png" if table.reference.value == "preterm_postnatal" else "ig_nbs"
    measure_name = {
        "weight": "weight",
        "length": "len",
        "head_circumference": "hc",
        "weight_for_length": "wfl",
    }[table.indicator.value]
    source = ROOT / "intergrowth" / f"{family}_{measure_name}_male_zscores.csv"
    coordinates = []
    measurements = []
    for line in source.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if "+" in fields[0]:
            weeks, days = fields[0].split("+")
            x = int(weeks) * 7 + int(days)
        else:
            x = float(fields[0])
        if table.get_min_range() <= x <= table.get_max_range():
            coordinates.append(x)
            measurements.append(float(fields[4]))  # Published median z=0.
    assert len(coordinates) >= 3
    if table.indicator.value == "weight_for_length":
        args = {"coordinates": coordinates}
    else:
        age_type = AgeType.POSTMENSTRUAL if family == "ig_png" else AgeType.GESTATIONAL
        unit = AgeUnit.WEEKS if family == "ig_png" else AgeUnit.DAYS
        args = {"ages": coordinates, "age_definition": AgeDefinition(age_type, unit)}
    scores, references = calc.calculate_numpy(
        indicator=table.get_table_type().value,
        measurements=measurements,
        sexes="M",
        **args,
    )
    assert all(ref == table.get_file_name() for ref in references)
    np.testing.assert_allclose(scores, 0, atol=0.16 if measure_name != "weight" else 0.20)
