"""Exhaustive boundary-grid properties for all six predefined GrowthPlans.

Official clinical rules are distinguished from user-defined source precedence.
Numeric checks do not independently establish clinical indications.
"""

from __future__ import annotations

import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator, Indicator
from pedgrowth.data.cdc import CdcClinicalPlan, CdcPlan, CdcWithWhoFallbackPlan, WhoWithCdcFallbackPlan
from pedgrowth.data.who2006 import WhoPlan
from pedgrowth.exceptions import DataNotFoundError

AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)
PLANS = (
    WhoPlan,
    CdcPlan,
    CdcWithWhoFallbackPlan,
    WhoWithCdcFallbackPlan,
    CdcClinicalPlan,
)
AGES = (
    0,
    0.1,
    2,
    3,
    12,
    23.999,
    24,
    36,
    60,
    60.5,
    60.99,
    61,
    100,
    120,
    121,
    180,
    228,
    229,
    239.999,
    240,
    260,
)


@pytest.mark.parametrize("plan_type", PLANS, ids=lambda cls: cls.__name__)
@pytest.mark.parametrize("sex", ["M", "F"])
@pytest.mark.parametrize("indicator", list(Indicator))
def test_all_reference_selection_properties_and_scalar_batch_parity(plan_type, sex, indicator):
    plan = plan_type()
    calc = GrowthChartsCalculator(plan=plan)
    kwargs = {
        "indicator": indicator,
        "sex": sex,
        "age_definition": AGE,
    }
    if indicator.value in ("wfl", "wfh"):
        kwargs["coordinate"] = 85.0
    ages = list(AGES)
    values = []
    for age in ages:
        try:
            result = plan.resolve(age=age, **kwargs)
        except DataNotFoundError:
            result = None
        values.append(result)
        if result is not None:
            if isinstance(plan, WhoPlan):
                assert result.reference_id.startswith("who")
            if isinstance(plan, CdcPlan):
                assert result.reference_id.startswith("cdc")
            if isinstance(plan, CdcClinicalPlan):
                assert (
                    result.reference_id.startswith("who")
                    if age < 24
                    else result.reference_id.startswith("cdc")
                )
                assert 0 <= age < 240
                if indicator is Indicator.BMI_FOR_AGE:
                    assert age >= 24
    expected = [r.reference_id if r else "" for r in values]
    numpy_scores, reference_ids = calc.calculate_numpy(
        indicator=indicator,
        ages=ages,
        age_definition=AGE,
        measurements=[20.0] * len(ages),
        sexes=sex,
        coordinates=[85.0] * len(ages) if indicator.value in ("wfl", "wfh") else None,
        errors="coerce",
    )
    assert list(reference_ids) == expected
    assert len(numpy_scores) == len(ages)
    for index, item in enumerate(values):
        if item is not None:
            assert calc.resolve(age=ages[index], **kwargs) == item


@pytest.mark.parametrize("age", [0, 3, 12, 23.9, 24, 36, 100, 228, 239])
def test_user_precedence_plans_only_fallback_on_missing_reference(age):
    first_cdc = CdcWithWhoFallbackPlan()
    first_who = WhoWithCdcFallbackPlan()
    cdc = CdcPlan()
    who = WhoPlan()
    for indicator in Indicator:
        args = {
            "indicator": indicator,
            "sex": "F",
            "age": age,
            "age_definition": AGE,
            **({"coordinate": 80.0} if indicator.value in ("wfl", "wfh") else {}),
        }
        for first, second, combined in (
            (cdc, who, first_cdc),
            (who, cdc, first_who),
        ):
            try:
                wanted = first.resolve(**args)
            except DataNotFoundError:
                try:
                    wanted = second.resolve(**args)
                except DataNotFoundError:
                    with pytest.raises(DataNotFoundError):
                        combined.resolve(**args)
                    continue
            actual = combined.resolve(**args)
            assert actual.reference_id == wanted.reference_id


def test_generic_factories_have_same_reference_policy_as_named_plans():
    from pedgrowth.registry import create_plan

    selectors = (
        (create_plan("who"), WhoPlan()),
        (create_plan("cdc"), CdcPlan()),
        (create_plan("cdc_with_who_fallback"), CdcWithWhoFallbackPlan()),
        (create_plan("who_with_cdc_fallback"), WhoWithCdcFallbackPlan()),
        (create_plan("cdc_clinical"), CdcClinicalPlan()),
    )
    for factory_plan, named_plan in selectors:
        for age in (12, 24, 36, 100):
            expected = named_plan.resolve(
                indicator="wfa",
                sex="M",
                age=age,
                age_definition=AGE,
            )
            observed = factory_plan.resolve(
                indicator="wfa",
                sex="M",
                age=age,
                age_definition=AGE,
            )
            assert observed.reference_id == expected.reference_id
