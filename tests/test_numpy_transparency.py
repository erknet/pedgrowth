"""Array inputs use optional NumPy transparently; scalar calls do not."""

from __future__ import annotations

import sys

import numpy as np
import pytest
from pedgrowth import GrowthChartsCalculator
from pedgrowth.exceptions import InvalidMeasurement


def test_scalar_and_numpy_inputs_same_public_method() -> None:
    calc = GrowthChartsCalculator()
    scalar = calc.wfa(10.4, 22.45, "M")
    assert isinstance(scalar, float)
    values = np.array([10.4, 11.2, 8.9], dtype=np.float64)
    months = np.array([22.45, 23.0, 20.0], dtype=np.float64)
    arr = calc.wfa(values, months, "M")
    assert isinstance(arr, np.ndarray)
    assert arr.dtype == np.float64
    np.testing.assert_allclose(
        arr,
        [calc.wfa(float(x), float(y), "M") for x, y in zip(values, months, strict=True)],
        rtol=1e-12,
        atol=1e-12,
    )
    assert isinstance(calc.wfa(np.float64(10.4), np.float64(22.45), "M"), float)


def test_broadcast_scalar_index_or_measurement() -> None:
    calc = GrowthChartsCalculator()
    values = np.asarray([8, 10, 11], dtype=np.int64)
    ages = np.asarray([12, 18, 24], dtype=np.int64)
    np.testing.assert_allclose(
        calc.wfa(values, 18, "F"),
        [calc.wfa(float(value), 18, "F") for value in values],
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        calc.wfa(10.4, ages, "F"),
        [calc.wfa(10.4, float(age), "F") for age in ages],
        rtol=1e-12,
        atol=1e-12,
    )
    assert calc.zscores_numpy("wfa", values, 18, "F").shape == (3,)
    assert calc.zscores_numpy("wfa", 10.4, ages, "F").shape == (3,)


@pytest.mark.parametrize(
    "indicator,measurements,index",
    [
        ("bmifa", [17.2, 20.5, 22.0], [65.0, 87.0, 110.0]),
        ("hcfa", [43.3, 47.4, 49.5], [12.0, 25.0, 40.0]),
        ("muacfa", [12.7, 13.4, 15.8], [3.0, 10.0, 35.0]),
        ("tsfa", [8.3, 9.9, 10.4], [3.0, 10.0, 35.0]),
        ("ssfa", [5.3, 6.9, 7.1], [3.0, 10.0, 35.0]),
    ],
)
def test_numpy_generic_indicator_dispatch(indicator, measurements, index) -> None:
    calc = GrowthChartsCalculator()
    values = np.asarray(measurements)
    ages = np.asarray(index)
    array = calc.zscore_for_measurement(indicator, values, "M", ages)
    assert isinstance(array, np.ndarray)
    np.testing.assert_allclose(
        array,
        [calc.zscore_for_measurement(indicator, x, "M", t) for x, t in zip(measurements, index, strict=True)],
        atol=1e-12,
        rtol=1e-12,
    )


def test_extreme_cdc_bmi_works_with_numpy_alone(monkeypatch) -> None:
    # Prevent SciPy from importing even if installed in the test environment.
    monkeypatch.setitem(sys.modules, "scipy", None)
    monkeypatch.setitem(sys.modules, "scipy.special", None)
    c = GrowthChartsCalculator(standard="cdc", interpolation="linear")
    bmi = np.array([18.1, 20.3, 22.6, 28.0])
    age = np.array([50.5, 50.7, 51.0, 53.0])
    expected = [c.bmifa(float(b), float(a), "M") for b, a in zip(bmi, age, strict=True)]
    result = c.bmifa(bmi, age, "M")
    assert isinstance(result, np.ndarray)
    np.testing.assert_allclose(result, expected, rtol=1e-12, atol=1e-12)


def test_array_failure_is_not_silently_replaced_by_scalar() -> None:
    c = GrowthChartsCalculator()
    with pytest.raises(InvalidMeasurement):
        c.wfa(np.array([[10.4, 11.0]]), np.array([[22.0, 23.0]]), "M")
