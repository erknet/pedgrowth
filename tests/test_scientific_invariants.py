"""Scientific invariants across every implemented model, plus error semantics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator, Sex
from pedgrowth.data.cdc import CdcClinicalPlan, CdcPlan
from pedgrowth.data.cdc.tables import CDC_TABLES
from pedgrowth.data.intergrowth import IntergrowthPlan
from pedgrowth.data.intergrowth.intergrowth_tables import (
    INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthWeightForAge,
)
from pedgrowth.data.who2006 import WhoPlan
from pedgrowth.exceptions import DataNotFoundError, InvalidMeasurement, InvalidSexError

from tests.reference_sets import WHO_TABLES

ALL_EQUATIONS = (
    *INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthWeightForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
)
AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)


@pytest.mark.parametrize("table_class", [*WHO_TABLES, *CDC_TABLES], ids=lambda cls: cls.__name__)
def test_lms_zscore_strictly_increasing_and_scalar_vector_agree(table_class):
    table = table_class()
    sex = table.get_table_sex() or Sex.Male
    x = table.get_min_range() + 0.4 * (table.get_max_range() - table.get_min_range())
    lms = table.get_lms(x, sex)
    values = np.asarray([0.6, 0.8, 0.95, 1, 1.05, 1.2, 1.8]) * lms.m
    calc = GrowthChartsCalculator(table=table)
    kwargs = (
        {"ages": [x] * len(values), "age_definition": AGE}
        if table.get_table_type().value not in ("wfl", "wfh")
        else {"coordinates": [x] * len(values)}
    )
    scalar = np.asarray([table.calculate_zscore(x, float(value), sex) for value in values])
    score, references = calc.calculate_numpy(
        indicator=table.get_table_type().value,
        measurements=values,
        sexes=["male" if sex is Sex.Male else "female"] * len(values),
        **kwargs,
    )
    assert np.all(np.diff(scalar) > 0)
    assert np.isfinite(scalar).all()
    np.testing.assert_allclose(score, scalar, rtol=1e-11, atol=1e-10)
    assert all(ref == table.get_file_name() for ref in references)


@pytest.mark.parametrize("table_class", ALL_EQUATIONS, ids=lambda cls: cls.__name__)
def test_equation_zscore_increases_with_measurement(table_class):
    table = table_class()
    x = (table.get_max_range() + table.get_min_range()) / 2
    samples = [
        table.calculate_zscore(x, measurement, Sex.Male)
        for measurement in (
            (1, 2, 4, 6) if table.get_table_type().value in ("wfa", "wfl") else (15, 25, 40, 65)
        )
    ]
    assert np.isfinite(samples).all()
    assert np.all(np.diff(samples) > 0)


@pytest.mark.parametrize(
    "unit,converted",
    [
        (AgeUnit.DAYS, 365.25),
        (AgeUnit.WEEKS, 365.25 / 7),
        (AgeUnit.MONTHS, 12),
        (AgeUnit.YEARS, 1),
    ],
)
def test_age_units_cannot_change_reference_or_zscore(unit, converted):
    calc = GrowthChartsCalculator(plan=WhoPlan())
    row = calc.calculate(
        indicator="wfa",
        measurement=10.5,
        age=converted,
        age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, unit),
        sex="M",
    )
    baseline = calc.calculate(
        indicator="wfa",
        measurement=10.5,
        age=12,
        age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
        sex="M",
    )
    assert row.reference_id == baseline.reference_id == "who_weight_for_age_boys"
    assert row.zscore == pytest.approx(baseline.zscore, abs=1e-12)


@pytest.mark.parametrize(
    "age_type",
    [
        AgeType.GESTATIONAL,
        AgeType.POSTMENSTRUAL,
        AgeType.CORRECTED,
    ],
)
def test_chronological_reference_does_not_implicitly_convert_clinical_age(age_type):
    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
    with pytest.raises(ValueError, match="chronological"):
        calc.calculate(
            indicator="wfa",
            measurement=12,
            sex="M",
            age=24,
            age_definition=AgeDefinition(age_type, AgeUnit.MONTHS),
        )


@pytest.mark.parametrize("measure", [float("nan"), float("inf"), -1, 0, -float("inf")])
def test_invalid_measurement_never_generates_finite_zscore(measure):
    calc = GrowthChartsCalculator(plan=CdcPlan())
    with pytest.raises((ValueError, InvalidMeasurement)):
        calc.calculate(
            indicator="wfa",
            measurement=measure,
            sex="M",
            age=30,
            age_definition=AGE,
        )
    scores, refs = calc.calculate_numpy(
        indicator="wfa",
        measurements=[measure, 12],
        sexes=["M", "M"],
        ages=[30, 30],
        age_definition=AGE,
        errors="coerce",
    )
    assert np.isnan(scores[0])
    assert np.isfinite(scores[1])
    assert refs[0] == ""
    assert refs[1].startswith("cdc_")


@pytest.mark.parametrize("sex", ["", "other", "unknown", "0", "X"])
def test_invalid_sex_never_silently_chooses_reference(sex):
    calc = GrowthChartsCalculator(plan=WhoPlan())
    with pytest.raises(InvalidSexError):
        calc.zscore(indicator="wfa", measurement=9, sex=sex, age=12, age_definition=AGE)


def test_reference_metadata_matches_selected_plan_and_immutable_source_hash():
    who = GrowthChartsCalculator(plan=WhoPlan()).available_references()
    cdc = GrowthChartsCalculator(plan=CdcPlan()).available_references()
    ig = GrowthChartsCalculator(plan=IntergrowthPlan()).available_references()
    assert len(who) == 24 and all(name.startswith("who") for name in who)
    assert len(cdc) == 9 and all(name.startswith("cdc") for name in cdc)
    assert len(ig) == 4 and all(name.startswith("intergrowth") for name in ig)
    assert all(len(item.data_sha256) == 64 for group in (who, cdc, ig) for item in group.values())
    assert Path("packages/pedgrowth-data-intergrowth/src/pedgrowth/data/intergrowth/intergrowth.py").is_file()


@pytest.mark.parametrize("age", [-1, float("nan"), float("inf"), 240, 300])
def test_clinical_plan_rejects_unsupported_ages(age):
    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
    with pytest.raises((DataNotFoundError, ValueError)):
        calc.resolve(indicator="bmifa", age=age, age_definition=AGE, sex="M")
