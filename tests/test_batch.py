"""Parity and performance assertions for NumPy/SciPy bulk evaluation."""

from __future__ import annotations

import numpy as np
import pytest
from pedgrowth import GrowthChartsCalculator, Sex
from pedgrowth.data.cdc.tables import CDC_TABLES
from pedgrowth.exceptions import DataNotFoundError, InvalidMeasurement


@pytest.mark.parametrize(
    ("indicator", "sex", "idx", "meas"),
    [
        ("wfa", "M", [0, 1, 12, 48, 61, 100, 120], [3.3464, 5.0, 10, 15, 18, 40, 31.1]),
        ("bmifa", "F", [0, 2, 24, 61, 120, 200], [13.3, 15, 18, 18, 22, 29]),
        ("lfa", "F", [0, 12, 36, 61, 120, 228], [49, 75, 90, 109.6, 140, 163.1]),
        ("wfl", "M", [45, 60, 75, 90, 100], [2.45, 6, 11, 15, 25]),
        ("wfh", "F", [65, 77, 99, 120], [7.2, 10.2, 20, 29]),
        ("muacfa", "M", [3, 8, 15, 48], [13.48, 16, 9, 20]),
        ("tsfa", "F", [3, 12, 40], [10, 16, 4]),
        ("ssfa", "M", [3, 12, 40], [7.7, 15, 3]),
    ],
)
def test_who_vectorized_matches_scalar(indicator, sex, idx, meas):
    calculator = GrowthChartsCalculator()
    vector = calculator.zscores_numpy(indicator, np.array(meas), np.array(idx), sex)
    scalar = [calculator.zscore_for_measurement(indicator, m, sex, i) for m, i in zip(meas, idx, strict=True)]
    assert np.allclose(vector, scalar, rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("use_extended", [True, False])
def test_cdc_vectorized_lms_and_extended_bmi(use_extended):
    from pedgrowth.data.cdc.tables import CdcBmiForAge2000

    selected = CDC_TABLES if use_extended else [CdcBmiForAge2000]
    calculator = GrowthChartsCalculator(override_tables=selected)
    indices = np.array([24, 60, 120, 200, 240.5] * 12, dtype=float)
    measurements = np.linspace(12, 25, len(indices))
    vector = calculator.zscores_numpy("bmifa", measurements, indices, Sex.Male)
    scalar = np.array(
        [calculator.bmifa(float(m), float(i), "M") for m, i in zip(measurements, indices, strict=True)]
    )
    np.testing.assert_allclose(vector, scalar, atol=1e-11, rtol=1e-11)


def test_vector_cdc_fallback_and_aliases():
    c = GrowthChartsCalculator(include_cdc=True)
    x = np.array([24.0, 60.0, 100.0, 130.0, 180.0, 220.0])
    y = np.array([11.0, 19.0, 30.0, 40.0, 52.0, 60.0])
    np.testing.assert_allclose(
        c.zscores_numpy("wfa", y, x, "F"),
        [c.wfa(float(m), float(i), "F") for m, i in zip(y, x, strict=True)],
        atol=1e-11,
    )
    x = np.array([70.0, 80.0, 100.0])
    y = np.array([10.0, 12.0, 19.0])
    np.testing.assert_allclose(
        c.zscores_numpy("wfl", y, x, "M"),
        [c.wfl(float(m), "M", float(i)) for m, i in zip(y, x, strict=True)],
        atol=1e-11,
    )


def test_adjustment_vectorized_parity():
    c = GrowthChartsCalculator(adjust_height_data=True)
    x = np.array([75.0, 90.0, 100.0])
    y = np.array([10.0, 14.0, 23.0])
    np.testing.assert_allclose(
        c.zscores_numpy("wfl", y, x, "F", is_recumbent_height=False),
        [c.wfl(float(m), "F", float(i), is_recumbent_height=False) for m, i in zip(y, x, strict=True)],
        rtol=1e-11,
        atol=1e-11,
    )


def test_vector_rejects_invalid_values():
    c = GrowthChartsCalculator()
    with pytest.raises(InvalidMeasurement):
        c.zscores_numpy("wfa", [1.0, 2.0], [3.0], "M")
    with pytest.raises(InvalidMeasurement):
        c.zscores_numpy("wfa", [float("nan")], [3.0], "M")
    with pytest.raises(InvalidMeasurement):
        c.zscores_numpy("wfa", [-1.0], [3.0], "M")
    with pytest.raises(InvalidMeasurement):
        c.zscores_numpy("wfa", [True], [3.0], "M")
    with pytest.raises(InvalidMeasurement):
        c.zscores_numpy("wfa", [[1.0, 2.0]], [[1.0, 2.0]], "M")
    with pytest.raises(DataNotFoundError):
        c.zscores_numpy("wfa", [13.0], [500.0], "M")
    assert c.zscores_numpy("wfa", [], [], "M").shape == (0,)
