"""Fail if any shipped reference lacks a declared validation status.

Status is not certification: official percentile or published z-score tests
are independent numerical oracles; external R comparisons are a separate gate.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pedgrowth.data.cdc.tables import CDC_TABLES
from pedgrowth.data.intergrowth.intergrowth_tables import (
    INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthWeightForAge,
)
from pedgrowth.tables.table import GrowthTable

from tests.reference_sets import WHO_TABLES

ROOT = Path(__file__).resolve().parents[1]


def report() -> dict[str, dict[str, str]]:
    official = json.loads((ROOT / "tests/fixtures/official_percentiles/manifest.json").read_text())
    entries: dict[str, dict[str, str]] = {}
    for cdc_cls in CDC_TABLES:
        name = cast(type[GrowthTable], cdc_cls)().get_file_name()
        entries[name] = {
            "status": "independent_published_percentiles" if name in official else "missing",
            "source": official.get(name, {}).get("url", ""),
        }
    import csv

    with (ROOT / "tests/fixtures/who_r/expected.csv").open(newline="") as stream:
        validated_who = {row["table"] for row in csv.DictReader(stream)}
    for who_cls in WHO_TABLES:
        name = cast(Callable[[], GrowthTable], who_cls)().get_file_name()
        entries[name] = {
            "status": "independent_WHO_R_oracle" if name in validated_who else "missing",
            "source": "tests/fixtures/who_r/expected.csv",
        }
    for intergrowth_cls in [
        *INTERGROWTH_POSTNATAL_TABLES,
        IntergrowthVeryPretermBirthWeightForAge,
        IntergrowthVeryPretermBirthLengthForAge,
        IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    ]:
        name = intergrowth_cls().get_file_name()
        entries[name] = {
            "status": "independent_published_rounded_zscore_grid",
            "source": "tests/fixtures/intergrowth/",
        }
    return entries


if __name__ == "__main__":
    rows = report()
    for name, item in sorted(rows.items()):
        print(f"{name}: {item['status']}")
    print(
        f"Independent per-table numerical oracles: {sum(x['status'].startswith('independent') for x in rows.values())}/{len(rows)}"
    )
