"""External publication examples and explicit calculation-policy regression tests.

Sources:
WHO anthroplus README (WHO 2007 reference; 100-month male sample):
https://github.com/WorldHealthOrganization/anthroplus
CDC Extended BMI data-file worked examples:
https://www.cdc.gov/growthcharts/extended-bmi-data-files.htm
Values are externally published, NOT derived from this package's fixtures.
"""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pytest
from pedgrowth import GrowthChartsCalculator, InterpolationPolicy, MeasurementPosition, ReferenceStandard, Sex
from pedgrowth.data.cdc.tables import CdcBmiForAge
from pedgrowth.exceptions import DataNotFoundError


def test_who_anthroplus_official_example_three_indicators() -> None:
    # WHO's anthroplus package example: male, 100 months, 100 cm, 30 kg,
    # published HAZ -5.04, WAZ +0.87, BAZ +5.03.
    calc = GrowthChartsCalculator(standard="who", interpolation="linear")
    assert calc.lhfa(100, 100, "M") == pytest.approx(-5.04, abs=0.015)
    assert calc.wfa(30, 100, "M") == pytest.approx(0.87, abs=0.015)
    assert calc.bmifa(30, 100, "M") == pytest.approx(5.03, abs=0.015)


def test_cdc_official_extended_bmi_example_with_published_p95() -> None:
    # CDC worked example: male 50.5 months, BMI 22.6; P95 17.8219,
    # sigma 2.3983, and raw LMS from the official data file.
    calc = GrowthChartsCalculator(standard=ReferenceStandard.CDC)
    row = CdcBmiForAge().get_lms(50.5, Sex.Male)
    assert row.p95 == pytest.approx(17.8219, abs=1e-10)
    assert row.sigma == pytest.approx(2.3983, abs=0.0001)
    expected = NormalDist().inv_cdf(0.90 + 0.10 * NormalDist().cdf((22.6 - 17.8219) / 2.398288))
    assert calc.bmifa(22.6, 50.5, "M") == pytest.approx(expected, abs=1e-12)
    # Published below-P95 worked example: girl 114.5 mo, BMI 21.2,
    # L=-2.257782149, M=16.57626713, S=.132796819.
    expected_below = ((21.2 / 16.57626713) ** (-2.257782149) - 1) / (-2.257782149 * 0.132796819)
    assert calc.bmifa(21.2, 114.5, "F") == pytest.approx(expected_below, abs=1e-12)


def test_published_p95_not_the_lms_derived_value() -> None:
    table = CdcBmiForAge()
    row = table.get_lms(50.5, Sex.Male)
    assert row.p95 is not None
    # The data-file P95 is rounded, so this intentionally differs from an
    # LMS-derived P95. The cutoff must use the published column.
    derived = row.m * (1 + row.l * row.s * NormalDist().inv_cdf(0.95)) ** (1 / row.l)
    assert row.p95 != derived
    assert table.calculate_zscore(50.5, row.p95 + 0.000001, Sex.Male) > 1.64


def test_cdc_interpolated_sigma_uses_published_polynomial() -> None:
    for sex in (Sex.Male, Sex.Female):
        row = CdcBmiForAge().get_lms(51.0, sex, InterpolationPolicy.LINEAR)
        age = 51.0 / 12
        expected = (
            0.3728 + 0.5196 * age - 0.0091 * age * age
            if sex is Sex.Male
            else 0.8334 + 0.3712 * age - 0.0011 * age * age
        )
        assert row.sigma == pytest.approx(expected, abs=1e-12)
        assert row.p95 is not None
        assert row.p95 > 0


def test_reference_standard_policy_precedence() -> None:
    a = GrowthChartsCalculator()
    assert a.standard is ReferenceStandard.WHO
    assert a.interpolation is InterpolationPolicy.NEAREST
    who = GrowthChartsCalculator(standard="who")
    cdc = GrowthChartsCalculator(standard="cdc")
    who_first = GrowthChartsCalculator(standard="who_then_cdc")
    cdc_first = GrowthChartsCalculator(standard="cdc_then_who")
    assert who_first.wfa(10, 24, "M") == pytest.approx(who.wfa(10, 24, "M"))
    assert cdc_first.wfa(10, 24, "M") == pytest.approx(cdc.wfa(10, 24, "M"))
    assert cdc_first.wfa(10, 24, "M") != pytest.approx(who_first.wfa(10, 24, "M"))
    with pytest.raises(DataNotFoundError):
        who.wfa(40, 145, "M")
    assert who_first.wfa(40, 145, "M") == pytest.approx(cdc.wfa(40, 145, "M"))
    with pytest.raises(ValueError, match="Specify either"):
        GrowthChartsCalculator(include_cdc=True, standard="cdc")
    with pytest.raises(ValueError, match="Cannot combine"):
        GrowthChartsCalculator(override_tables=[], standard="cdc")


def test_linear_interpolation_is_continuous_and_keeps_endpoints() -> None:
    c = GrowthChartsCalculator(standard="who", interpolation="linear")
    nearest = GrowthChartsCalculator(standard="who", interpolation="nearest")
    age = 100.35
    z0 = c.wfa(29, 100, "M")
    z1 = c.wfa(29, 101, "M")
    zmid = c.wfa(29, age, "M")
    assert min(z0, z1) <= zmid <= max(z0, z1)
    assert zmid != pytest.approx(nearest.wfa(29, age, "M"), abs=1e-6)
    assert c.wfa(29, 100, "M") == pytest.approx(nearest.wfa(29, 100, "M"), abs=1e-12)


@pytest.mark.parametrize("standard", ["who", "cdc", "who_then_cdc", "cdc_then_who"])
@pytest.mark.parametrize("interpolation", ["linear", "nearest"])
def test_batch_matches_scalar_for_each_policy(standard: str, interpolation: str) -> None:
    c = GrowthChartsCalculator(standard=standard, interpolation=interpolation)
    ages = np.array([25.4, 30.5, 43.2, 50.5, 59.8], dtype=np.float64)
    bmi = np.array([16.0, 17.5, 19.2, 24.6, 22.4], dtype=np.float64)
    bulk = c.zscores_numpy("bmifa", bmi, ages, "M")
    scalar = [c.bmifa(float(x), float(y), "M") for x, y in zip(bmi, ages, strict=True)]
    np.testing.assert_allclose(bulk, scalar, rtol=1e-11, atol=1e-11)


def test_cdc_p95_linear_vector_consistent_at_midmonth() -> None:
    c = GrowthChartsCalculator(standard="cdc", interpolation="linear")
    xs = np.array([50.5, 50.6, 50.9, 51, 51.4, 51.5])
    bmi = np.array([17.82, 17.84, 18.0, 22.6, 25.0, 19.1])
    expected = [c.bmifa(float(b), float(x), "M") for b, x in zip(bmi, xs, strict=True)]
    np.testing.assert_allclose(c.zscores_numpy("bmifa", bmi, xs, "M"), expected, atol=1e-11)


def test_typed_measurement_position_retains_legacy_behavior() -> None:
    calc = GrowthChartsCalculator(adjust_height_data=True)
    modern = calc.lhfa(88, 18, "F", position=MeasurementPosition.RECUMBENT)
    old = calc.lhfa(88, 18, "F", is_recumbent_height=True)
    assert modern == pytest.approx(old, abs=1e-12)
    assert calc.wfl(12, "F", 80, position="standing") == pytest.approx(
        calc.wfl(12, "F", 80, is_recumbent_height=False)
    )
    with pytest.raises(ValueError, match="Conflicting"):
        calc.lhfa(
            88,
            18,
            "F",
            is_recumbent_height=True,
            position="standing",
        )
    with pytest.raises(ValueError):
        calc.lhfa(88, 18, "F", position="nonsense")
    via_vector = calc.zscores_numpy(
        "wfl",
        np.array([12.0]),
        np.array([80.0]),
        "F",
        position=MeasurementPosition.STANDING,
    )
    assert via_vector[0] == pytest.approx(calc.wfl(12, "F", 80, position=MeasurementPosition.STANDING))
