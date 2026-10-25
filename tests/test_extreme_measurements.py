"""Numerical stress validation independent of routine LMS regression values.

Tests are explicitly about finite behavior, tails, continuity, and scalar/
vector agreement. They do not assign a clinical meaning to implausible values.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator, Sex
from pedgrowth.data.cdc.tables import CDC_TABLES, CdcBmiForAge
from pedgrowth.data.intergrowth.intergrowth_tables import (
    INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthWeightForAge,
)
from pedgrowth.data.who2006.tables import WhoWeightForAgeBoys
from pedgrowth.exceptions import InvalidMeasurement
from pedgrowth.tables.math import extended_bmi_z
from pedgrowth.tables.table import AGE_BASED_TYPES
from scipy.special import log_ndtr, ndtri_exp

from tests.reference_sets import WHO_TABLES

AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)


@pytest.mark.parametrize("table_class", (*WHO_TABLES, *CDC_TABLES), ids=lambda factory: factory.__name__)
def test_every_lms_table_extreme_positive_values_scalar_batch_consistency(table_class):
    table = table_class()
    calculator = GrowthChartsCalculator(table=table)
    sex = table.get_table_sex() or Sex.Male
    x = table.get_min_range() + (table.get_max_range() - table.get_min_range()) * 0.375
    if table.get_file_name().startswith("cdc_") and table.get_table_type().value in (
        "wfa",
        "bmifa",
        "hfa",
        "hcfa",
        "lfa",
    ):
        # A native reference knot avoids conflating CDC month interpolation
        # with the extreme-measurement stress test.
        key = sex if table.get_col_index_sex() is not None else None
        keys = table._indices[key]
        x = float(keys[len(keys) // 3])
    m = table.get_lms(x, sex).m
    factors = (0.001, 0.025, 0.10, 0.5, 1.0, 2.0, 10.0, 1e3)
    values = [m * factor for factor in factors]
    expected = []
    for value in values:
        try:
            result = table.calculate_zscore(x, value, sex)
        except InvalidMeasurement:
            expected.append(None)
        else:
            assert math.isfinite(result)
            expected.append(result)
    args = (
        {"ages": x, "age_definition": AGE}
        if table.get_table_type() in AGE_BASED_TYPES
        else {"coordinates": x}
    )
    scores, refs = calculator.calculate_numpy(
        indicator=table.get_table_type().value,
        sexes=sex.value,
        measurements=values,
        errors="coerce",
        **args,
    )
    for index, target in enumerate(expected):
        if target is None:
            assert math.isnan(scores[index])
            assert refs[index] == ""
        else:
            assert math.isfinite(scores[index])
            assert scores[index] == pytest.approx(target, abs=1e-8, rel=1e-11)
            assert refs[index] == table.get_file_name()
    accepted = [z for z in expected if z is not None]
    assert all(b > a for a, b in zip(accepted, accepted[1:], strict=False))


@pytest.mark.parametrize("excess", (0, 0.1, 1, 3, 5.99, 6, 7, 8, 10, 20, 50, 100, 200, 1000))
def test_cdc_extreme_bmi_stable_against_independent_scipy_special_functions(excess):
    reference = float(-ndtri_exp(math.log(0.1) + log_ndtr(-excess)))
    actual = extended_bmi_z(excess)
    assert math.isfinite(actual)
    assert actual == pytest.approx(reference, rel=2e-11, abs=1e-8)


@pytest.mark.parametrize("sex", (Sex.Male, Sex.Female))
@pytest.mark.parametrize("age", (24.5, 36.5, 100.5, 156.5, 239.5))
def test_cdc_extreme_bmi_across_sexes_and_age_boundaries(age, sex):
    table = CdcBmiForAge()
    coeff = table.get_lms(age, sex)
    assert coeff.p95 is not None and coeff.sigma is not None
    calculator = GrowthChartsCalculator(table=table)
    factors = (0.0000001, 0.01, 0.1, 1, 3, 6, 8, 20, 50, 100)
    bmi_values = [coeff.p95 + factor * coeff.sigma for factor in factors]
    z, refs = calculator.calculate_numpy(
        indicator="bmifa",
        sexes=sex.value,
        measurements=bmi_values,
        ages=age,
        age_definition=AGE,
    )
    assert np.isfinite(z).all()
    assert list(refs) == [table.get_file_name()] * len(bmi_values)
    for i, factor in enumerate(factors):
        independent = float(-ndtri_exp(math.log(0.1) + log_ndtr(-factor)))
        assert z[i] == pytest.approx(independent, abs=1e-7)
        assert table.calculate_zscore(age, bmi_values[i], sex) == pytest.approx(z[i], abs=1e-8)


@pytest.mark.parametrize("value", (1e-300, 1e-200, 1e-30, 1e30, 1e200, 1e300))
def test_who_sd_tail_extremely_positive_finite_inputs(value):
    table = WhoWeightForAgeBoys()
    score = table.calculate_zscore(12.0, value, Sex.Male)
    assert math.isfinite(score)
    calculator = GrowthChartsCalculator(table=table)
    vector, _ = calculator.calculate_numpy(
        indicator="wfa",
        sexes="M",
        ages=12.0,
        age_definition=AGE,
        measurements=[value],
    )
    assert vector[0] == pytest.approx(score, rel=1e-12, abs=1e-7)


@pytest.mark.parametrize("value", (1e-300, 1e-200, 1e-30, 0.0, -1, float("nan"), float("inf")))
def test_unsupported_extreme_measurements_have_explicit_error_or_missing(value):
    from pedgrowth.data.cdc.tables import CdcBmiForAge2000

    table = CdcBmiForAge2000()
    calculator = GrowthChartsCalculator(table=table)
    if value <= 0 or not math.isfinite(value) or value < 1e-100:
        with pytest.raises(InvalidMeasurement):
            table.calculate_zscore(100.5, value, Sex.Male)
    else:
        try:
            scalar = table.calculate_zscore(100.5, value, Sex.Male)
        except InvalidMeasurement:
            pass
        else:
            assert math.isfinite(scalar)
    scores, refs = calculator.calculate_numpy(
        indicator="bmifa",
        sexes="M",
        ages=100.5,
        age_definition=AGE,
        measurements=[value],
        errors="coerce",
    )
    assert not math.isinf(scores[0])
    if math.isnan(scores[0]):
        assert refs[0] == ""


@pytest.mark.parametrize("value", (1e10, 1e30, 1e150, 1e300))
def test_excessively_high_bmi_never_overflows_or_rounds_to_infinity(value):
    assert extended_bmi_z(value) == pytest.approx(value, rel=5e-10)


@pytest.mark.parametrize(
    "table_class",
    (
        *INTERGROWTH_POSTNATAL_TABLES,
        IntergrowthVeryPretermBirthWeightForAge,
        IntergrowthVeryPretermBirthLengthForAge,
        IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    ),
    ids=lambda cls: cls.__name__,
)
@pytest.mark.parametrize("sex", (Sex.Male, Sex.Female))
def test_intergrowth_extremes_and_strict_domain(table_class, sex):
    from pedgrowth.exceptions import DataNotFoundError

    table = table_class()
    coordinate = (table.get_min_range() + table.get_max_range()) / 2
    values = (1e-300, 1e-100, 1e-5, 0.1, 1, 10, 1e6, 1e100, 1e300)
    scores = [table.calculate_zscore(coordinate, value, sex) for value in values]
    assert all(math.isfinite(z) for z in scores)
    # Linear models cannot resolve tiny differences below floating-point
    # precision relative to the intercept, but must never reverse order.
    assert all(b >= a for a, b in zip(scores, scores[1:], strict=False))
    assert scores[-1] > scores[4]
    calc = GrowthChartsCalculator(table=table)
    if table.indicator.value == "weight_for_length":
        args = {"coordinates": [coordinate] * len(values)}
    else:
        category = (
            AgeType.POSTMENSTRUAL if table.reference.value == "preterm_postnatal" else AgeType.GESTATIONAL
        )
        unit = AgeUnit.WEEKS if category is AgeType.POSTMENSTRUAL else AgeUnit.DAYS
        args = {"ages": [coordinate] * len(values), "age_definition": AgeDefinition(category, unit)}
    observed, refs = calc.calculate_numpy(
        indicator=table.get_table_type().value,
        sexes=sex.value,
        measurements=list(values),
        **args,
    )
    np.testing.assert_allclose(observed, scores, rtol=1e-12, atol=1e-10)
    assert all(ref == table.get_file_name() for ref in refs)
    for invalid in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            table.calculate_zscore(coordinate, invalid, sex)
    with pytest.raises((ValueError, DataNotFoundError)):
        table.calculate_zscore(table.get_max_range() + 0.01, 1.5, sex)
