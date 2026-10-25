"""Official published percentile observations independently validate CDC tables.

Fixture values are downloaded from CDC percentile columns, not calculated by
GrowthCharts. Snapshot source hashes and fixture hashes are pinned.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import NormalDist

import pytest
from pedgrowth.data.cdc.tables import CDC_TABLES
from pedgrowth.tables.sex import Sex

FIXTURES = Path(__file__).parent / "fixtures/official_percentiles"
CATALOG = json.loads((FIXTURES / "manifest.json").read_text())
PERCENTILES = {"p3": 0.03, "p5": 0.05, "p50": 0.50, "p95": 0.95}


@pytest.mark.parametrize("table_class", CDC_TABLES, ids=lambda cls: cls.__name__)
def test_every_cdc_table_against_published_percentiles(table_class):
    table = table_class()
    name = table.get_file_name()
    source = FIXTURES / f"{name}.csv"
    assert name in CATALOG, f"{name}: missing independently sourced validation data"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == CATALOG[name]["fixture_sha256"]
    checked = 0
    largest = 0.0
    with source.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            coordinate = float(row["coordinate"])
            if not table.get_min_range() <= coordinate <= table.get_max_range():
                continue
            sex = Sex.Male if row["sex"] in ("1", "M") else Sex.Female
            measurement = float(row["measurement"])
            expected = NormalDist().inv_cdf(PERCENTILES[row["percentile"]])
            observed = table.calculate_zscore(coordinate, measurement, sex)
            difference = abs(observed - expected)
            largest = max(largest, difference)
            assert difference < 0.035, (name, sex, coordinate, row["percentile"], observed, expected)
            checked += 1
    assert checked >= 100, f"{name}: insufficient independently published percentile cases: {checked}"
    assert checked == CATALOG[name]["observations"]
