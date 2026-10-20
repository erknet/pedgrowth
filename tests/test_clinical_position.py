"""Measurement-position conversions checked against WHO R and CDC chart conventions."""

from __future__ import annotations

import numpy as np
import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator, Sex
from pedgrowth.data.cdc import CdcClinicalPlan
from pedgrowth.data.who2006 import WhoPlan

from tests.reference_sets import WHO_TABLES

AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)


def test_who_below_two_standing_to_recumbent_matches_official_r():
    # Official WHO anthro: age 365 days, measure='H' adds 0.7 cm for length.
    table = next(cls() for cls in WHO_TABLES if cls().get_file_name() == "who_length_for_age_boys")
    months = 365 / 30.4375
    median_length = table.get_lms(months, Sex.Male).m
    standing_height = median_length - 0.7
    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
    chosen = calc.resolve(indicator="hfa", sex="M", age=months, age_definition=AGE)
    assert chosen.reference_id == "who_length_for_age_boys"
    assert chosen.measurement_offset == pytest.approx(0.7)
    assert calc.zscore(
        indicator="hfa", sex="M", age=months, age_definition=AGE, measurement=standing_height
    ) == pytest.approx(0, abs=1e-5)
    z, ids = calc.calculate_numpy(
        indicator="hfa",
        sexes=["male", "M"],
        ages=[months] * 2,
        measurements=[standing_height] * 2,
        age_definition=AGE,
    )
    np.testing.assert_allclose(z, 0, atol=1e-5)
    assert all(i == chosen.reference_id for i in ids)


def test_who_older_recumbent_to_standing():
    table = next(cls() for cls in WHO_TABLES if cls().get_file_name() == "who_length_for_age_boys")
    months = 900 / 30.4375
    standing = table.get_lms(months, Sex.Male).m
    calc = GrowthChartsCalculator(plan=WhoPlan())
    chosen = calc.resolve(indicator="lfa", age=months, age_definition=AGE, sex="M")
    assert chosen.measurement_offset == pytest.approx(-0.7)
    assert calc.zscore(
        indicator="lfa", sex="M", age=months, age_definition=AGE, measurement=standing + 0.7
    ) == pytest.approx(0, abs=1e-5)


def test_cdc_clinical_position_after_24_months():
    from pedgrowth.data.cdc.tables import CdcHeightForAge, CdcWeightForHeight

    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
    stature = CdcHeightForAge().get_lms(36, Sex.Female).m
    result = calc.calculate(indicator="lfa", sex="F", age=36, age_definition=AGE, measurement=stature + 0.7)
    assert result.reference_id == "cdc_height_for_age_24_240"
    assert result.zscore == pytest.approx(0, abs=1e-5)
    height = 90.0
    wfh_median = CdcWeightForHeight().get_lms(height, Sex.Female).m
    result = calc.calculate(
        indicator="wfl", sex="F", age=36, age_definition=AGE, coordinate=height + 0.7, measurement=wfh_median
    )
    assert result.reference_id == "cdc_weight_for_height"
    assert result.zscore == pytest.approx(0, abs=1e-5)
    score, references = calc.calculate_numpy(
        indicator="wfl",
        sexes=["female", "F"],
        ages=[36, 36],
        age_definition=AGE,
        coordinates=[90.7, 90.7],
        measurements=[wfh_median, wfh_median],
    )
    np.testing.assert_allclose(score, 0, atol=1e-5)
    assert list(references) == [result.reference_id] * 2


def test_cdc_clinical_position_below_24_months():
    from pedgrowth.data.who2006.tables.weight_for_length_boys import WhoWeightForLengthBoys

    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
    median = WhoWeightForLengthBoys().get_lms(80, Sex.Male).m
    resolved = calc.resolve(indicator="wfh", sex="M", age=12, age_definition=AGE, coordinate=79.3)
    assert resolved.reference_id == "who_weight_for_length_boys"
    assert resolved.coordinate == pytest.approx(80)
    assert calc.zscore(
        indicator="wfh", sex="M", age=12, age_definition=AGE, coordinate=79.3, measurement=median
    ) == pytest.approx(0, abs=1e-5)


@pytest.mark.parametrize("age", [239.99, 240, 240.01])
def test_clinical_upper_boundary_from_cdc_r(age):
    from pedgrowth.exceptions import DataNotFoundError

    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
    if age < 240:
        assert calc.resolve(indicator="bmifa", sex="M", age=age, age_definition=AGE)
    else:
        with pytest.raises(DataNotFoundError):
            calc.resolve(indicator="bmifa", sex="M", age=age, age_definition=AGE)
