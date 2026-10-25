"""Verify offline scientific oracle provenance, coverage and reference snapshot identity."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from pedgrowth.data.cdc.tables import CDC_TABLES

from tests.reference_sets import WHO_TABLES

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_all_cdc_published_fixtures_match_source_provenance():
    cdc = json.loads((FIXTURES / "official_percentiles/manifest.json").read_text())
    upstream = json.loads((ROOT / "validation/source_data/SOURCES.json").read_text())["tables"]
    names = {cls().get_file_name() for cls in CDC_TABLES}
    assert set(cdc) == names
    for name, info in cdc.items():
        assert info["source_sha256"] == upstream[name]["source_sha256"]
        assert info["url"] == upstream[name]["source_url"]
        fixture = FIXTURES / "official_percentiles" / f"{name}.csv"
        assert digest(fixture) == info["fixture_sha256"]
        with fixture.open(newline="") as file:
            assert len(list(csv.DictReader(file))) == info["observations"]


def test_all_who_r_fixtures_have_immutable_inputs_and_expected_outputs():
    base = FIXTURES / "who_r"
    baseline = json.loads((base / "manifest.json").read_text())
    challenges = json.loads((base / "challenges_manifest.json").read_text())
    positions = json.loads((base / "position_manifest.json").read_text())
    assert digest(base / "inputs.csv") == baseline["inputs_sha256"]
    assert digest(base / "expected.csv") == baseline["expected_sha256"]
    assert digest(base / "challenges_input.csv") == challenges["input_sha256"]
    assert digest(base / "challenges_expected.csv") == challenges["expected_sha256"]
    assert digest(base / "position_inputs.csv") == positions["input_sha256"]
    assert digest(base / "position_expected.csv") == positions["expected_sha256"]
    with (base / "challenges_expected.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert challenges["cases"] == len(rows)
    assert sum(bool(row["expected"]) for row in rows) == challenges["official_available"]
    assert {row["table"] for row in rows} == {cls().get_file_name() for cls in WHO_TABLES}


def test_intergrowth_published_zscore_snapshots_have_pinned_hashes():
    reference = FIXTURES / "intergrowth"
    manifest = json.loads((reference / "manifest.json").read_text())
    files = {file.name for file in reference.glob("ig_*.csv")}
    assert len(files) == 14
    assert files == set(manifest["files"])
    for name, expected in manifest["files"].items():
        assert digest(reference / name) == expected


def test_continuous_gigs_oracle_and_policy_specification_are_immutable():
    intergrowth = FIXTURES / "intergrowth"
    oracle = json.loads((intergrowth / "continuous_manifest.json").read_text())
    assert oracle["upstream_release"] == "v0.5.2"
    assert digest(intergrowth / "continuous_inputs.csv") == oracle["inputs_sha256"]
    assert digest(intergrowth / "continuous_expected.csv") == oracle["expected_sha256"]
    assert sum(oracle["per_table"].values()) == oracle["case_count"] == 4970
    assert len(oracle["per_table"]) == 7
    specification = json.loads((FIXTURES / "policy_review_manifest.json").read_text())
    assert digest(FIXTURES / "policy_review.csv") == specification["sha256"]
    assert specification["cases"] >= 60


def test_clinical_external_examples_and_r_outputs_are_sha256_pinned():
    clinical = FIXTURES / "clinical_cases_manifest.json"
    manifest = json.loads(clinical.read_text())
    assert digest(FIXTURES / "clinical_cases_input.csv") == manifest["original_inputs_sha256"]
    assert digest(FIXTURES / "clinical_cases_expected.csv") == manifest["expected_results_sha256"]
    assert manifest["cases"] == manifest["published_scenarios"] + manifest["independent_r_scenarios"]
    assert manifest["published_scenarios"] >= 3
