"""Scalar, NumPy, Pandas and plan boundary cross-validation."""

import numpy as np
import pandas as pd
import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator
from pedgrowth.data.cdc import CdcClinicalPlan, CdcPlan, CdcWithWhoFallbackPlan, WhoWithCdcFallbackPlan
from pedgrowth.data.intergrowth import IntergrowthPlan
from pedgrowth.data.who2006 import WhoPlan
from pedgrowth.exceptions import PyGrowUpError
from pedgrowth.pandas_integration import calculate_typed_dataframe

AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)


@pytest.mark.parametrize(
    "plan", [WhoPlan, CdcPlan, CdcClinicalPlan, CdcWithWhoFallbackPlan, WhoWithCdcFallbackPlan]
)
@pytest.mark.parametrize(
    "indicator,values,ages",
    [
        ("wfa", [9, 10, 13, 18, 27], [11, 23.99, 24, 36, 100]),
        ("bmifa", [16, 17, 18, 19, 21], [11, 23.99, 24, 36, 100]),
        ("hcfa", [44, 45, 46, 49, 50], [11, 23.99, 24, 36, 100]),
    ],
)
def test_plan_matrix_scalar_numpy_pandas(plan, indicator, values, ages):
    calc = GrowthChartsCalculator(plan=plan())
    sexes = ["M", "F", "M", "F", "M"]
    expected = []
    for value, age, sex in zip(values, ages, sexes, strict=True):
        try:
            expected.append(
                calc.calculate(indicator=indicator, measurement=value, age=age, age_definition=AGE, sex=sex)
            )
        except (LookupError, ValueError, PyGrowUpError):
            expected.append(None)
    scores, refs = calc.calculate_numpy(
        indicator=indicator,
        measurements=values,
        ages=ages,
        age_definition=AGE,
        sexes=sexes,
        errors="coerce",
    )
    df = pd.DataFrame({"value": values, "age": ages, "sex": sexes})
    out = calculate_typed_dataframe(
        df,
        calc,
        indicator=indicator,
        measurement="value",
        age="age",
        sex="sex",
        age_definition=AGE,
        errors="coerce",
    )
    for i, reference in enumerate(expected):
        if reference is None:
            assert np.isnan(scores[i])
        else:
            assert scores[i] == pytest.approx(reference.zscore, abs=1e-10)
            assert refs[i] == reference.reference_id
    np.testing.assert_allclose(out.zscore.to_numpy(), scores, equal_nan=True)
    assert out.reference_id.tolist() == list(refs)


def test_batch_coerce_invalid_measurement_and_sex():
    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
    z, refs = calc.calculate_numpy(
        indicator="wfa",
        measurements=[10, -1, 11, 12],
        ages=[12, 12, 24, 36],
        sexes=["M", "M", "invalid", "F"],
        age_definition=AGE,
        errors="coerce",
    )
    assert np.isfinite(z[0]) and np.isfinite(z[3])
    assert np.isnan(z[1]) and np.isnan(z[2])
    assert refs[1] == refs[2] == ""


def test_intergrowth_requires_postmenstrual_age():
    calc = GrowthChartsCalculator(plan=IntergrowthPlan())
    with pytest.raises(ValueError):
        calc.calculate(indicator="wfa", measurement=2, sex="M", age=35, age_definition=AGE)


def test_batch_plan_does_not_call_scalar_resolver(monkeypatch):
    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())

    def forbidden(*args, **kwargs):
        raise AssertionError("Per-row scalar resolution must not run")

    monkeypatch.setattr(calc.plan, "resolve", forbidden)
    z, ids = calc.calculate_numpy(
        indicator="wfa",
        measurements=np.repeat(12.0, 100),
        ages=np.linspace(12, 40, 100),
        sexes=np.repeat("M", 100),
        age_definition=AGE,
    )
    assert np.isfinite(z).all()
    assert all(ids)


def test_reference_domain_and_direct_equation_table():
    from pedgrowth import CoordinateType
    from pedgrowth.data.intergrowth import IntergrowthPretermWeightForLength

    calc = GrowthChartsCalculator(table=IntergrowthPretermWeightForLength())
    result = calc.resolve(indicator="wfl", sex="F", coordinate=48)
    assert result.domain.coordinate_type is CoordinateType.LENGTH
    assert result.domain.minimum <= 48 <= result.domain.maximum
    assert np.isfinite(calc.calculate(indicator="wfl", sex="F", coordinate=48, measurement=2.7).zscore)


@pytest.mark.parametrize(
    "factory,ages,definition,measurement",
    [
        (WhoPlan, np.linspace(6, 62, 2048), AGE, 11.0),
        (CdcPlan, np.linspace(6, 220, 2048), AGE, 14.0),
        (CdcClinicalPlan, np.linspace(12, 225, 2048), AGE, 13.0),
        (CdcWithWhoFallbackPlan, np.linspace(6, 220, 2048), AGE, 13.0),
        (WhoWithCdcFallbackPlan, np.linspace(6, 220, 2048), AGE, 13.0),
        (
            IntergrowthPlan,
            np.linspace(28, 63, 2048),
            AgeDefinition(AgeType.POSTMENSTRUAL, AgeUnit.WEEKS),
            2.0,
        ),
    ],
)
def test_batch_reference_selection_never_invokes_scalar_policy(
    monkeypatch,
    factory,
    ages,
    definition,
    measurement,
):
    """Mask selection must not degrade to per-row scalar dispatch."""
    from pedgrowth.registry import registry

    plan = factory()

    def forbidden(*args, **kwargs):
        raise AssertionError("Scalar selection was invoked inside a NumPy batch")

    monkeypatch.setattr(plan, "resolve", forbidden)
    if hasattr(plan, "_resolve_row"):
        monkeypatch.setattr(plan, "_resolve_row", forbidden)
    monkeypatch.setattr(registry, "candidates", forbidden)
    monkeypatch.setattr(registry, "accept_table", forbidden)
    z, refs = GrowthChartsCalculator(plan=plan).calculate_numpy(
        indicator="wfa",
        measurements=np.full(len(ages), measurement),
        ages=ages,
        sexes=np.where(np.arange(len(ages)) % 2, "F", "M"),
        age_definition=definition,
        errors="coerce",
    )
    assert z.shape == (len(ages),)
    assert refs.shape == (len(ages),)
    assert np.any(refs != "")


@pytest.mark.parametrize(
    "factory",
    [WhoPlan, CdcPlan, CdcClinicalPlan, CdcWithWhoFallbackPlan, WhoWithCdcFallbackPlan],
)
@pytest.mark.parametrize("indicator", ["wfa", "lfa", "hfa", "wfl", "wfh", "bmifa"])
def test_vectorized_reference_selection_exact_scalar_parity(factory, indicator):
    """Boundary, invalid rows and position corrections must preserve selection."""
    from pedgrowth.exceptions import PyGrowUpError

    plan = factory()
    ages = np.array([0, 1, 11, 23.99, 24, 24.01, 36, 60, 100, 120, 180, 239, 240, 260, np.nan])
    coordinate = np.linspace(38.0, 121.0, len(ages))
    sexes = np.array(["M", "F", "male", " female ", "x"] * 3)
    results, failures = plan.resolve_numpy(
        indicator=indicator,
        sexes=sexes,
        ages=ages,
        age_definition=AGE,
        coordinates=coordinate,
    )
    for i in range(len(ages)):
        try:
            expected = plan.resolve(
                indicator=indicator,
                sex=str(sexes[i]),
                age=float(ages[i]),
                age_definition=AGE,
                coordinate=float(coordinate[i]),
            )
        except (PyGrowUpError, ValueError, TypeError) as exc:
            assert results[i] is None
            assert failures[i] is not None
            assert isinstance(failures[i], type(exc))
        else:
            assert failures[i] is None
            assert results[i] is not None
            assert results[i].reference_id == expected.reference_id
            assert results[i].coordinate == pytest.approx(expected.coordinate, abs=1e-10)
            assert results[i].measurement_offset == pytest.approx(expected.measurement_offset, abs=1e-10)


def test_intergrowth_vectorized_reference_selection_parity():
    plan = IntergrowthPlan()
    age_definition = AgeDefinition(AgeType.POSTMENSTRUAL, AgeUnit.WEEKS)
    ages = np.array([25, 27, 28, 35, 42, 50, 63, 64, 65, np.nan])
    coordinates = np.linspace(37, 70, len(ages))
    sexes = ["M", "F", "M", "F", "male", "female", "M", "F", "M", "unknown"]
    for indicator in ("wfa", "wfl"):
        expected, errors = plan.resolve_numpy(
            indicator=indicator,
            sexes=sexes,
            ages=ages,
            age_definition=age_definition,
            coordinates=coordinates,
        )
        for i in range(len(ages)):
            try:
                row = plan.resolve(
                    indicator=indicator,
                    sex=sexes[i],
                    age=float(ages[i]),
                    age_definition=age_definition,
                    coordinate=float(coordinates[i]),
                )
            except (ValueError, PyGrowUpError) as exc:
                assert expected[i] is None
                assert isinstance(errors[i], type(exc))
            else:
                assert errors[i] is None
                assert expected[i] == row
