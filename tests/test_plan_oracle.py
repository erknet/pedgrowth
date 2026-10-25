"""Manually curated WHO/CDC selection-policy cases, independent of resolve()."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator
from pedgrowth.exceptions import DataNotFoundError
from pedgrowth.registry import create_plan

ROWS = list(csv.DictReader((Path(__file__).parent / "fixtures/plan_resolution.csv").open()))
AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)


@pytest.mark.parametrize(
    "row", ROWS, ids=lambda row: "-".join((row["plan"], row["indicator"], row["sex"], row["age_months"]))
)
def test_predefined_plan_resolution_oracle(row):
    plan_name = {
        "WhoPlan": "who",
        "CdcPlan": "cdc",
        "CdcClinicalPlan": "cdc_clinical",
        "CdcWithWhoFallbackPlan": "cdc_with_who_fallback",
        "WhoWithCdcFallbackPlan": "who_with_cdc_fallback",
    }[row["plan"]]
    plan = create_plan(plan_name)
    params = dict(
        indicator=row["indicator"], sex=row["sex"], age=float(row["age_months"]), age_definition=AGE
    )
    if row["coordinate"]:
        params["coordinate"] = float(row["coordinate"])
    if row["expected_table"] == "none":
        with pytest.raises(DataNotFoundError):
            plan.resolve(**params)
        return
    resolved = plan.resolve(**params)
    assert resolved.reference_id == row["expected_table"]
    calc = GrowthChartsCalculator(plan=plan)
    assert calc.resolve(**params).reference_id == row["expected_table"]
    scores, refs = calc.calculate_numpy(
        indicator=row["indicator"],
        sexes=[row["sex"]],
        ages=[float(row["age_months"])],
        age_definition=AGE,
        coordinates=[float(row["coordinate"])] if row["coordinate"] else None,
        measurements=[15],
        errors="coerce",
    )
    assert refs[0] == row["expected_table"]
