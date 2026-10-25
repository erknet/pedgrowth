"""Frozen WHO R anthro/anthroplus expected z-scores per concrete table."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
from pedgrowth.tables.sex import Sex

from tests.reference_sets import WHO_TABLES

FIXTURE = Path(__file__).parent / "fixtures/who_r/expected.csv"
MANIFEST = json.loads(FIXTURE.with_name("manifest.json").read_text())


def test_who_baseline_fixture_integrity():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == MANIFEST["expected_sha256"]
    assert (
        hashlib.sha256(FIXTURE.with_name("inputs.csv").read_bytes()).hexdigest() == MANIFEST["inputs_sha256"]
    )


ROWS = list(csv.DictReader(FIXTURE.open()))
COUNTS = Counter(row["table"] for row in ROWS)


@pytest.mark.parametrize("table_class", WHO_TABLES, ids=lambda cls: cls.__name__)
def test_each_who_table_against_official_r(table_class):
    table = table_class()
    rows = [row for row in ROWS if row["table"] == table.get_file_name()]
    assert len(rows) >= 12, f"Missing WHO R validation for {table.get_file_name()}: {len(rows)}"
    for row in rows:
        sex = Sex.Male if row["sex"] == "M" else Sex.Female
        actual = table.calculate_zscore(float(row["coordinate"]), float(row["measurement"]), sex)
        expected = float(row["expected"])
        assert actual == pytest.approx(expected, abs=0.07), (table.get_file_name(), row, actual)
