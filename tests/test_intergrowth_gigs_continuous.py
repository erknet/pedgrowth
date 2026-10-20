"""Independent continuous R gigs v0.5.2 reference verification of all 7 tables.

Official original upstream R functions generate expected results, not this Python
library. Inputs are seeded independently of GrowthCharts model coefficients.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pytest
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator
from pedgrowth.data.intergrowth import IntergrowthCalculator, IntergrowthPlan
from pedgrowth.data.intergrowth.intergrowth_tables import (
    INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthWeightForAge,
)
from pedgrowth.tables import Sex

ROOT = Path(__file__).parent / "fixtures/intergrowth"
MANIFEST = json.loads((ROOT / "continuous_manifest.json").read_text())
TABLES = [
    *INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthWeightForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
]


def _read_oracles() -> dict[str, list[dict[str, str]]]:
    input_file = ROOT / "continuous_inputs.csv"
    output_file = ROOT / "continuous_expected.csv"
    assert hashlib.sha256(input_file.read_bytes()).hexdigest() == MANIFEST["inputs_sha256"]
    assert hashlib.sha256(output_file.read_bytes()).hexdigest() == MANIFEST["expected_sha256"]
    with input_file.open(newline="", encoding="utf-8") as handle:
        inputs = list(csv.DictReader(handle))
    with output_file.open(newline="", encoding="utf-8") as handle:
        outputs = list(csv.DictReader(handle))
    assert len(inputs) == len(outputs) == MANIFEST["case_count"] == 4970
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item, expected in zip(inputs, outputs, strict=True):
        for field in ("family", "indicator", "sex", "scenario"):
            assert item[field] == expected[field]
        assert float(item["coordinate"]) == pytest.approx(float(expected["coordinate"]), abs=1e-12)
        assert float(item["measurement"]) == pytest.approx(float(expected["measurement"]), abs=1e-12)
        assert expected["expected"] and np.isfinite(float(expected["expected"]))
        grouped[f"{item['family']}_{item['indicator']}"].append(expected)
    return grouped


CASES = _read_oracles()


@pytest.mark.parametrize("table_class", TABLES, ids=lambda cls: cls.__name__)
def test_all_continuous_r_gigs_cases_scalar_and_numpy(table_class):
    table = table_class()
    family = table.reference.value
    indicator = table.indicator.value
    name = f"{family}_{indicator}"
    cases = CASES[name]
    assert len(cases) == MANIFEST["per_table"][name] == 710
    assert {"M", "F"} == {c["sex"] for c in cases}
    assert {"boundary", "random", "extreme"} <= {c["scenario"] for c in cases}
    model = IntergrowthCalculator(family)
    direct = GrowthChartsCalculator(table=table)
    x = np.array([float(c["coordinate"]) for c in cases])
    y = np.array([float(c["measurement"]) for c in cases])
    sex = [c["sex"] for c in cases]
    official = np.array([float(c["expected"]) for c in cases])
    calculated = np.array(
        [model.zscore(indicator, float(m), float(a), s) for a, m, s in zip(x, y, sex, strict=True)]
    )
    np.testing.assert_allclose(calculated, official, rtol=0, atol=2e-10)
    if indicator == "weight_for_length":
        kwargs = {"coordinates": x}
    else:
        age_type = AgeType.POSTMENSTRUAL if family == "preterm_postnatal" else AgeType.GESTATIONAL
        age_unit = AgeUnit.WEEKS if family == "preterm_postnatal" else AgeUnit.DAYS
        kwargs = {"ages": x, "age_definition": AgeDefinition(age_type, age_unit)}
    numpy_results, refs = direct.calculate_numpy(
        indicator=table.get_table_type().value,
        sexes=sex,
        measurements=y,
        **kwargs,
    )
    np.testing.assert_allclose(numpy_results, official, rtol=0, atol=2e-10)
    assert all(ref == table.get_file_name() for ref in refs)


@pytest.mark.parametrize("sex", [Sex.Male, Sex.Female])
def test_postnatal_plan_independent_r_equations(sex):
    calc = GrowthChartsCalculator(plan=IntergrowthPlan())
    rows = CASES["preterm_postnatal_weight"]
    samples = [r for r in rows if r["sex"] == sex.value][::23]
    assert len(samples) > 10
    for row in samples:
        result = calc.calculate(
            indicator="wfa",
            measurement=float(row["measurement"]),
            sex=sex,
            age=float(row["coordinate"]),
            age_definition=AgeDefinition(AgeType.POSTMENSTRUAL, AgeUnit.WEEKS),
        )
        assert result.reference_id == "intergrowth_preterm_postnatal_weight"
        assert result.zscore == pytest.approx(float(row["expected"]), abs=2e-10)
