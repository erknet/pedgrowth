import numpy as np
import pandas as pd
import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator, Indicator, Sex
from pedgrowth.data.cdc import CdcClinicalPlan, CdcPlan
from pedgrowth.data.intergrowth import IntergrowthPlan, IntergrowthVeryPretermBirthWeightForAge
from pedgrowth.data.who2006 import WhoPlan
from pedgrowth.pandas_integration import calculate_typed_dataframe

AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)


def test_cdc_clinical_boundary_and_difference_from_cdc_first():
    clinical = CdcClinicalPlan()
    assert clinical.resolve(
        indicator=Indicator.WEIGHT_FOR_AGE, sex=Sex.Male, age=23.9, age_definition=AGE
    ).reference_id.startswith("who_")
    assert clinical.resolve(
        indicator=Indicator.WEIGHT_FOR_AGE, sex=Sex.Male, age=24, age_definition=AGE
    ).reference_id.startswith("cdc_")
    assert (
        CdcPlan()
        .resolve(indicator="wfa", sex="M", age=12, age_definition=AGE)
        .reference_id.startswith("cdc_")
    )
    with pytest.raises(ValueError):
        clinical.resolve(indicator="wfl", sex="M", coordinate=70)
    with pytest.raises(Exception) as exc:
        clinical.resolve(indicator="bmifa", sex="M", age=12, age_definition=AGE)
    assert "not recommended" in str(exc.value)


def test_scalar_numpy_and_pandas_agree():
    calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
    ages = np.array([12.0, 24.0, 36.0])
    values = np.array([10.0, 12.0, 14.0])
    sexes = ["M", "M", "F"]
    scalar = [
        calc.calculate(indicator="wfa", measurement=float(v), sex=s, age=float(a), age_definition=AGE)
        for v, s, a in zip(values, sexes, ages, strict=True)
    ]
    scores, refs = calc.calculate_numpy(
        indicator="wfa", measurements=values, sexes=sexes, ages=ages, age_definition=AGE
    )
    assert scores == pytest.approx([r.zscore for r in scalar])
    assert list(refs) == [r.reference_id for r in scalar]
    frame = pd.DataFrame({"age": ages, "weight": values, "sex": sexes})
    result = calculate_typed_dataframe(
        frame, calc, indicator="wfa", measurement="weight", sex="sex", age="age", age_definition=AGE
    )
    assert result.zscore.to_numpy() == pytest.approx(scores)
    assert result.reference_id.tolist() == list(refs)


def test_intergrowth_and_direct_birth():
    age = AgeDefinition(AgeType.POSTMENSTRUAL, AgeUnit.WEEKS)
    calc = GrowthChartsCalculator(plan=IntergrowthPlan())
    assert calc.calculate(
        indicator="wfa", sex="M", age=35, age_definition=age, measurement=2
    ).reference_id.startswith("intergrowth_")
    assert calc.calculate_numpy(
        indicator="wfa", sexes=["M", "F"], ages=[35, 36], measurements=[2, 2.2], age_definition=age
    )[0].shape == (2,)
    birth = GrowthChartsCalculator(table=IntergrowthVeryPretermBirthWeightForAge())
    assert birth.calculate(
        indicator="wfa",
        measurement=1.5,
        sex="M",
        age=210,
        age_definition=AgeDefinition(AgeType.GESTATIONAL, AgeUnit.DAYS),
    ).reference_id.startswith("intergrowth_very_preterm_birth")


def test_who_plan_and_strenum():
    assert isinstance(Indicator.WEIGHT_FOR_AGE, str)
    assert isinstance(Sex.Male, str)
    assert (
        WhoPlan()
        .resolve(indicator="wfa", sex="F", age=12, age_definition=AGE)
        .reference_id.startswith("who_")
    )
