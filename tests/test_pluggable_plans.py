"""External policy/model extension and mixed-validity vector input regressions."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from pedgrowth import (
    AgeDefinition,
    AgeType,
    AgeUnit,
    CsvGrowthTable,
    GrowthChartsCalculator,
    Indicator,
    ReferencePlan,
    ResolvedReference,
    Sex,
    TableDefinition,
    TableType,
)
from pedgrowth.data.intergrowth import IntergrowthPlan
from pedgrowth.exceptions import DataNotFoundError
from pedgrowth.provenance import ReferenceProvenance
from pedgrowth.tables.table import ReferenceTable

AGE = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)
WHO_SOURCE = Path(__file__).resolve().parents[1] / "validation/source_data/who_weight_for_age_boys.csv"


class StudyPlan:
    """A user-defined policy, not a subclass of a built-in plan."""

    def __init__(self, table: ReferenceTable) -> None:
        self.table = table

    def tables(self) -> tuple[ReferenceTable, ...]:
        return (self.table,)

    def resolve(
        self,
        *,
        indicator: Indicator | TableType | str,
        sex: Sex | str,
        age: float | None = None,
        age_definition: AgeDefinition | None = None,
        coordinate: float | None = None,
    ) -> ResolvedReference:
        if Indicator(indicator) is not Indicator.WEIGHT_FOR_AGE:
            raise DataNotFoundError("Only weight-for-age")
        if age_definition != AGE:
            raise ValueError("Use chronological months")
        if age is None or not self.table.get_min_range() <= age <= self.table.get_max_range():
            raise DataNotFoundError("Age outside reference")
        if sex not in (Sex.Male, "M"):
            raise DataNotFoundError("Sex outside reference")
        return ResolvedReference(self.table, age)


class CustomEquation(ReferenceTable):
    def get_file_name(self) -> str:
        return "custom_non_lms"

    def get_table_type(self) -> TableType:
        return TableType.WeightForAge

    def get_min_range(self) -> float:
        return 0.0

    def get_max_range(self) -> float:
        return 30.0

    def calculate_zscore(self, index_value, measurement, sex=None, interpolation=None):
        if not 0 <= index_value <= 30:
            raise DataNotFoundError("Outside reference")
        return (measurement - 10.0) / 2.0

    def get_provenance(self) -> ReferenceProvenance:
        return ReferenceProvenance(
            name=self.get_file_name(),
            standard="synthetic test only",
            reference_version="1",
            source_url=None,
            source_sha256=None,
            data_sha256="synthetic-constant",
            snapshot_date=None,
            custom=True,
        )


def test_custom_lms_table_plan_scalar_numpy_and_pandas(tmp_path: Path) -> None:
    import pandas as pd
    from pedgrowth.pandas_integration import calculate_typed_dataframe

    source = tmp_path / "study.csv"
    with WHO_SOURCE.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, ["sex", "index", "l", "m", "s", "sigma"])
        writer.writeheader()
        writer.writerows(rows)
    table = CsvGrowthTable(
        TableDefinition("independent_study", TableType.WeightForAge, source, Sex.Male, standard_name="study")
    )
    policy: ReferencePlan = StudyPlan(table)
    calc = GrowthChartsCalculator(plan=policy)
    scalar = calc.calculate(indicator="wfa", measurement=10.5, sex="M", age=18, age_definition=AGE)
    assert scalar.reference_id == "independent_study"
    assert (
        calc.available_references()["independent_study"].data_sha256
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )
    z, refs = calc.calculate_numpy(
        indicator="wfa", measurements=[10.5, 12.0], sexes=["M", "M"], ages=[18, 24], age_definition=AGE
    )
    assert z[0] == pytest.approx(scalar.zscore)
    assert list(refs) == ["independent_study", "independent_study"]
    frame = pd.DataFrame({"mass": [10.5, 12.0], "age": [18, 24], "sex": ["M", "M"]})
    result = calculate_typed_dataframe(
        frame, calc, indicator="wfa", measurement="mass", sex="sex", age="age", age_definition=AGE
    )
    np.testing.assert_allclose(result["zscore"], z)


def test_external_non_lms_table_supports_scalar_and_numpy() -> None:
    calc = GrowthChartsCalculator(plan=StudyPlan(CustomEquation()))
    scalar = calc.zscore(indicator="wfa", measurement=14, sex="M", age=18, age_definition=AGE)
    assert scalar == pytest.approx(2.0)
    values, refs = calc.calculate_numpy(
        indicator="wfa",
        measurements=[10, 12, 14],
        ages=[6, 12, 18],
        age_definition=AGE,
        sexes=["M", "M", "M"],
    )
    np.testing.assert_allclose(values, [0.0, 1.0, 2.0])
    assert list(refs) == ["custom_non_lms"] * 3
    assert calc.available_references()["custom_non_lms"].custom


def test_numpy_coerce_handles_nonnumeric_values_and_coordinates() -> None:
    calc = GrowthChartsCalculator(plan=StudyPlan(CustomEquation()))
    values, refs = calc.calculate_numpy(
        indicator="wfa",
        measurements=["10", "invalid", 14, "16"],
        sexes=["M", "M", "M", "M"],
        ages=["6", "12", "bad", "18"],
        age_definition=AGE,
        errors="coerce",
    )
    assert values[0] == pytest.approx(0.0)
    assert np.isnan(values[1]) and np.isnan(values[2])
    assert values[3] == pytest.approx(3.0)
    assert list(refs) == ["custom_non_lms", "", "", "custom_non_lms"]
    with pytest.raises(ValueError, match="numeric"):
        calc.calculate_numpy(
            indicator="wfa",
            measurements=[10, "wrong"],
            sexes=["M", "M"],
            ages=[10, 12],
            age_definition=AGE,
        )


def test_intergrowth_provenance_is_hash_of_coefficients_not_python_code() -> None:
    from pedgrowth.data.intergrowth.data import read_intergrowth_coefficients

    metadata = json.loads((WHO_SOURCE.parent / "INTERGROWTH_SOURCES.json").read_text())
    assert read_intergrowth_coefficients()
    calc = GrowthChartsCalculator(plan=IntergrowthPlan())
    for name, provenance in calc.available_references().items():
        assert name.startswith("intergrowth_")
        assert provenance.data_sha256 == metadata["sha256"]
    assert (
        metadata["sha256"]
        == hashlib.sha256((WHO_SOURCE.parent / "intergrowth_coefficients.json").read_bytes()).hexdigest()
    )
