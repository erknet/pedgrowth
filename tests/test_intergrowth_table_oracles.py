"""Validate each implemented INTERGROWTH equation table against published z-score grids."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pedgrowth.data.intergrowth.intergrowth_tables import (
    INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthWeightForAge,
)
from pedgrowth.tables.sex import Sex

FIXTURES = Path(__file__).parent / "fixtures/intergrowth"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
ALL = [
    *INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthWeightForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
]


@pytest.mark.parametrize("table_class", ALL, ids=lambda cls: cls.__name__)
@pytest.mark.parametrize("sex", [Sex.Male, Sex.Female])
def test_published_intergrowth_zscore_grid_by_concrete_table(table_class, sex):
    table = table_class()
    family = "ig_png" if "preterm_postnatal" in table.get_file_name() else "ig_nbs"
    measurement_name = {
        "weight": "weight",
        "length": "len",
        "head_circumference": "hc",
        "weight_for_length": "wfl",
    }[table.indicator.value]
    file = FIXTURES / f"{family}_{measurement_name}_{'male' if sex is Sex.Male else 'female'}_zscores.csv"
    assert file.is_file(), f"Missing independent source: {file}"
    assert hashlib.sha256(file.read_bytes()).hexdigest() == MANIFEST["files"][file.name]
    checked = 0
    for line in file.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if "+" in parts[0]:
            week, day = parts[0].split("+")
            x = int(week) * 7 + int(day)
        else:
            x = float(parts[0])
        if not table.get_min_range() <= x <= table.get_max_range():
            continue
        for expected_z, value in zip(range(-3, 4), parts[1:], strict=True):
            z = table.calculate_zscore(x, float(value), sex)
            tolerance = 0.20 if measurement_name == "weight" else 0.15
            assert abs(z - expected_z) < tolerance, (table.get_file_name(), sex, x, expected_z, z)
            checked += 1
    assert checked >= 20, f"Insufficient published observations for {table.get_file_name()}"
