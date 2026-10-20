"""Expanded WHO R oracle verification at reference boundaries and extreme tails.

Expected z-scores are obtained only from WHO anthro/anthroplus R, never from
the packaged LMS coefficients. Challenge measurements are deliberately chosen
around the LMS-defined z thresholds; they are not independent measurements.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
from pedgrowth.policies import InterpolationPolicy
from pedgrowth.tables import Sex

from tests.reference_sets import WHO_TABLES

ROOT = Path(__file__).parent / "fixtures/who_r"
INPUT = ROOT / "challenges_input.csv"
EXPECTED = ROOT / "challenges_expected.csv"
MANIFEST = json.loads((ROOT / "challenges_manifest.json").read_text())


def load() -> dict[str, list[tuple[dict[str, str], dict[str, str]]]]:
    with INPUT.open(newline="", encoding="utf-8") as left:
        input_rows = list(csv.DictReader(left))
    with EXPECTED.open(newline="", encoding="utf-8") as right:
        expected_rows = list(csv.DictReader(right))
    assert len(input_rows) == len(expected_rows) == MANIFEST["cases"]
    assert hashlib.sha256(INPUT.read_bytes()).hexdigest() == MANIFEST["input_sha256"]
    assert hashlib.sha256(EXPECTED.read_bytes()).hexdigest() == MANIFEST["expected_sha256"]
    cases: dict[str, list[tuple[dict[str, str], dict[str, str]]]] = {}
    for request, result in zip(input_rows, expected_rows, strict=True):
        assert request["table"] == result["table"]
        assert request["indicator"] == result["indicator"]
        assert request["sex"] == result["sex"]
        assert request["interpolation"] == result["interpolation"]
        assert float(request["coordinate"]) == pytest.approx(float(result["coordinate"]), abs=1e-10)
        cases.setdefault(request["table"], []).append((request, result))
    return cases


CASES = load()


@pytest.mark.parametrize("table_class", WHO_TABLES, ids=lambda cls: cls.__name__)
def test_who_table_against_expanded_official_r_reference(table_class):
    table = table_class()
    name = table.get_file_name()
    assert name in CASES, f"WHO R validation fixture missing: {name}"
    checked = 0
    excluded = 0
    levels: Counter[str] = Counter()
    interpolations: Counter[str] = Counter()
    for request, result in CASES[name]:
        age_or_length = float(request["coordinate"])
        if not result["expected"]:
            # WHO R anthro intentionally does not calculate ages above 1826
            # days even though coefficient snapshots contain extra boundary rows.
            assert name.startswith("who_")
            assert age_or_length * 30.4375 > 1826
            excluded += 1
            continue
        observed = table.calculate_zscore(
            age_or_length,
            float(request["measurement"]),
            Sex(request["sex"]),
            interpolation=InterpolationPolicy(request["interpolation"]),
        )
        official = float(result["expected"])
        # The WHO R z-score outputs round to two decimal places.
        assert observed == pytest.approx(official, abs=0.025), (
            name,
            request,
            observed,
            official,
        )
        checked += 1
        levels[request["target_z"]] += 1
        interpolations[request["interpolation"]] += 1
    assert checked >= 100, (name, checked)
    assert len(levels) >= 10, (name, levels)
    assert len(interpolations) >= 1
    assert checked + excluded == len(CASES[name])


def test_missing_official_who_outputs_are_explicitly_accounted_for():
    counts = Counter(row["table"] for cases in CASES.values() for _, row in cases if not row["expected"])
    assert sum(counts.values()) == MANIFEST["official_unavailable"]
    assert len(CASES) == 24
    assert sum(len(cases) for cases in CASES.values()) == MANIFEST["cases"]
