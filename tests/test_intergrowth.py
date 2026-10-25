"""Compare preterm formula implementations to independently published z-score tables."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from pedgrowth.data.intergrowth.intergrowth import IntergrowthCalculator

DATA = Path(__file__).parent / "fixtures" / "intergrowth"


@pytest.mark.parametrize(
    "family,reference", [("ig_png", "preterm_postnatal"), ("ig_nbs", "very_preterm_birth")]
)
@pytest.mark.parametrize(
    "measure,indicator,precision",
    [("weight", "weight", 0.01), ("len", "length", 0.1), ("hc", "head_circumference", 0.1)],
)
@pytest.mark.parametrize("sex", ["male", "female"])
def test_published_zscore_tables(
    family: str, reference: str, measure: str, indicator: str, precision: float, sex: str
) -> None:
    calc = IntergrowthCalculator(reference)
    source = DATA / f"{family}_{measure}_{sex}_zscores.csv"
    tested = 0
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        parts = line.split()
        if not parts:
            continue
        if family == "ig_png":
            age = float(parts[0])
        else:
            weeks, days = parts[0].split("+")
            age = int(weeks) * 7 + int(days)
            if age > 230:
                continue  # the full newborn standard switches statistical models here
        for z, value in zip(range(-3, 4), parts[1:], strict=True):
            measurement = float(value)
            estimated = calc.zscore(indicator, measurement, age, sex)
            # Published tables are rounded; check z against the implied rounding tolerance.
            assert math.isfinite(estimated)
            assert abs(estimated - z) < (0.2 if measure == "weight" else 0.12), (
                family,
                indicator,
                sex,
                age,
                z,
                estimated,
            )
            tested += 1
    assert tested >= 20


def test_intergrowth_outside_age_ranges() -> None:
    with pytest.raises(ValueError):
        IntergrowthCalculator("preterm_postnatal").zscore("weight", 2, 70, "M")
    with pytest.raises(ValueError):
        IntergrowthCalculator("very_preterm_birth").zscore("weight", 2, 231, "M")


@pytest.mark.parametrize("sex", ["male", "female"])
def test_published_postnatal_weight_for_length(sex: str) -> None:
    calc = IntergrowthCalculator("preterm_postnatal")
    source = DATA / f"ig_png_wfl_{sex}_zscores.csv"
    tested = 0
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        parts = line.split()
        length = float(parts[0])
        for z, value in zip(range(-3, 4), parts[1:], strict=True):
            observed = calc.zscore("weight_for_length", float(value), length, sex)
            assert abs(observed - z) < 0.15, (sex, length, z, observed)
            tested += 1
    assert tested >= 20
