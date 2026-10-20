"""Custom tables remain external, data-only, type-checked and isolated."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import numpy as np
import pytest
from pedgrowth import CsvGrowthTable, GrowthChartsCalculator, Sex, TableDefinition, TableType
from pedgrowth.exceptions import DataError, DataNotFoundError
from pedgrowth.tables.table import GrowthTable

SOURCE = Path(__file__).resolve().parents[1] / "validation/source_data/who_weight_for_age_boys.csv"


def make_modified_table(tmp_path: Path) -> Path:
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row["m"] = str(float(row["m"]) * 1.12)
    output = tmp_path / "new-growth-reference.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, ["sex", "index", "l", "m", "s", "sigma"])
        writer.writeheader()
        writer.writerows(rows)
    return output


def test_new_reference_can_be_registered_declaratively(tmp_path: Path) -> None:
    path = make_modified_table(tmp_path)
    external = TableDefinition(
        name="study_wfa_boys_2027",
        indicator=TableType.WeightForAge,
        source=path,
        sex=Sex.Male,
    )
    calc = GrowthChartsCalculator(additional_tables=[external])
    baseline = GrowthChartsCalculator()
    assert calc.wfa(10.4, 22.45, "M") != pytest.approx(baseline.wfa(10.4, 22.45, "M"))
    assert calc.wfa(10.4, 22.45, "F") == pytest.approx(baseline.wfa(10.4, 22.45, "F"))
    assert calc.bmifa(18.5, 50, "M") == pytest.approx(baseline.bmifa(18.5, 50, "M"))
    assert calc.table_source_hashes[external.name] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert isinstance(calc.find_table(TableType.WeightForAge, Sex.Male, 22.45), CsvGrowthTable)

    weights = np.array([10.4, 11.0, 12.1])
    months = np.array([22.45, 23.45, 25.3])
    np.testing.assert_allclose(
        calc.wfa(weights, months, "M"),
        [calc.wfa(float(x), float(t), "M") for x, t in zip(weights, months, strict=True)],
    )


def test_external_definition_does_not_allow_executable_csv(tmp_path: Path) -> None:
    path = make_modified_table(tmp_path)
    source = path.read_text(encoding="utf-8")
    path.write_text(source.replace("1.12", "__import__('os')", 1), encoding="utf-8")
    # Malformed input is rejected as data. No expression can be interpreted.
    definition = TableDefinition("untrusted_rows", TableType.WeightForAge, path, Sex.Male)
    with pytest.raises(DataError):
        GrowthChartsCalculator(additional_tables=[definition])


def test_external_declarations_validate_structure(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        TableDefinition("../outside", TableType.WeightForAge, SOURCE, Sex.Male)
    with pytest.raises(TypeError):
        TableDefinition("invalid_type", "wfa", SOURCE)
    with pytest.raises(ValueError):
        TableDefinition("wrong_indicator", TableType.WeightForAge, SOURCE, extended_bmi=True)
    d = TableDefinition("duplicate", TableType.WeightForAge, SOURCE, Sex.Male)
    with pytest.raises(DataError, match="Duplicate"):
        GrowthChartsCalculator(additional_tables=[d, d])
    collision = TableDefinition("who_weight_for_age_boys", TableType.WeightForAge, SOURCE, Sex.Male)
    with pytest.raises(DataError, match="Duplicate"):
        GrowthChartsCalculator(additional_tables=[collision])


def test_custom_subclass_can_override_algorithm_and_reference(tmp_path: Path) -> None:
    """Subclass extension is still supported for trusted custom algorithms."""

    class StudyGrowthTable(GrowthTable):
        def get_file_name(self) -> str:
            return "study_algorithm"

        def get_table_type(self) -> TableType:
            return TableType.WeightForAge

        def get_table_sex(self) -> Sex | None:
            return Sex.Male

        def get_col_index_sex(self) -> None:
            return None

        def get_table(self):
            from pedgrowth.reference_data import read_override_csv

            values, _ = read_override_csv(SOURCE)
            return values

        def calculate_zscore(self, index_value, measurement, sex=None, interpolation=None):
            from pedgrowth.policies import InterpolationPolicy

            return 2 + super().calculate_zscore(
                index_value,
                measurement,
                sex,
                interpolation=interpolation or InterpolationPolicy.NEAREST,
            )

    calc = GrowthChartsCalculator(override_tables=[StudyGrowthTable])
    z = GrowthChartsCalculator().wfa(10.4, 22.45, "M")
    assert calc.wfa(10.4, 22.45, "M") == pytest.approx(z + 2)
    with pytest.raises(DataNotFoundError):
        calc.wfa(10.4, 22.45, "F")
