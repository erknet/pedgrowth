"""API-diff version classification regression tests."""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from api_schema import classify, manifest  # noqa: E402
from auto_version import next_version  # noqa: E402


def test_schema_based_versioning(tmp_path: Path) -> None:
    original = manifest()
    baseline = tmp_path / "api-schema.json"
    baseline.write_text(json.dumps(original))
    assert next_version("1.0.0", baseline) == ("1.0.1", "patch")
    addition = copy.deepcopy(original)
    addition["modules"]["pedgrowth.pygrowup"]["GrowthChartsCalculator"]["members"]["new_method"] = {
        "parameters": []
    }
    assert classify(original, addition)[0] == "minor"
    changed = copy.deepcopy(original)
    changed["modules"]["pedgrowth.pygrowup"]["GrowthChartsCalculator"]["members"]["wfa"]["returns"] = "str"
    assert classify(original, changed)[0] == "major"
    removed = copy.deepcopy(original)
    del removed["modules"]["pedgrowth.pygrowup"]["GrowthChartsCalculator"]["members"]["wfa"]
    assert classify(original, removed)[0] == "major"


def test_enum_values_and_public_constants_are_versioned() -> None:
    current = manifest()
    enum = current["modules"]["pedgrowth.architecture"]["Indicator"]["members"]
    assert enum["WEIGHT_FOR_AGE"]["value"] == "'wfa'"
    changed = copy.deepcopy(current)
    changed["modules"]["pedgrowth.architecture"]["Indicator"]["members"]["WEIGHT_FOR_AGE"]["value"] = (
        "'different'"
    )
    assert classify(current, changed)[0] == "major"
    assert "ReferencePlan" in current["modules"]["pedgrowth"]["ReferencePlan"]["source"]


def test_overload_signatures_are_public_api() -> None:
    original = manifest()
    overloads = original["modules"]["pedgrowth.pygrowup"]["GrowthChartsCalculator"]["members"]["wfa"][
        "overloads"
    ]
    assert len(overloads) >= 2
    changed = copy.deepcopy(original)
    changed["modules"]["pedgrowth.pygrowup"]["GrowthChartsCalculator"]["members"]["wfa"]["overloads"][0][
        "returns"
    ] = "str"
    assert classify(original, changed)[0] == "major"


def test_missing_baseline_fails_closed() -> None:
    try:
        next_version("1.0.0", None)
    except ValueError as error:
        assert "Missing" in str(error)
    else:
        raise AssertionError("Expected failure without previous published schema")
