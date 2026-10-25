"""Compare platform/Python matrix numerical outcomes and reference identities."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def compare(files: list[Path], *, expected_versions: set[str] | None = None) -> dict[str, Any]:
    if len(files) < 2:
        raise ValueError("At least two independent environments must be compared")
    documents = [json.loads(path.read_text()) for path in files]
    baseline = documents[0]["observations"]
    if not baseline:
        raise AssertionError("Empty cross-platform reference-output baseline")
    versions = {str(result["python"]) for result in documents}
    if expected_versions and not expected_versions <= versions:
        raise AssertionError(f"Missing interpreters: {sorted(expected_versions - versions)}")
    systems = {str(result["platform"]) for result in documents}
    configurations = [(d["platform"], d["python"]) for d in documents]
    if len(set(configurations)) != len(configurations):
        raise AssertionError("Duplicate OS/Python matrix entry")
    max_abs = 0.0
    max_rel = 0.0
    for result in documents[1:]:
        observed = result["observations"]
        if set(observed) != set(baseline):
            raise AssertionError(
                f"Missing or additional scenarios in {result['platform']}/{result['python']}"
            )
        for case_id, ref in baseline.items():
            case = observed[case_id]
            if case["reference_id"] != ref["reference_id"]:
                raise AssertionError(f"Different references for {case_id} on {result['platform']}")
            actual = float(case["z"])
            expected = float(ref["z"])
            if not (math.isfinite(actual) and math.isfinite(expected)):
                raise AssertionError(f"Nonfinite result for {case_id}")
            difference = abs(actual - expected)
            max_abs = max(max_abs, difference)
            max_rel = max(max_rel, difference / max(1, abs(expected)))
            if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=2e-10):
                raise AssertionError(f"Different z-score for {case_id}: {expected} versus {actual}")
    print(
        f"Cross-runtime comparison passed: {len(files)} environments; "
        f"{len(baseline)} independent cases; max_abs={max_abs:.3g}; max_rel={max_rel:.3g}"
    )
    return {
        "environment_count": len(files),
        "scenarios": len(baseline),
        "systems": sorted(systems),
        "versions": sorted(versions),
        "maximum_absolute_difference": max_abs,
        "maximum_scaled_difference": max_rel,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--require-full-matrix", action="store_true")
    args = parser.parse_args()
    files = sorted(args.directory.rglob("repro-probe.json"))
    versions = {"3.11", "3.12", "3.13", "3.14"} if args.require_full_matrix else None
    compare(files, expected_versions=versions)
    if args.require_full_matrix:
        needed = {(os, python) for os in ("Linux", "Windows", "Darwin") for python in versions or ()}
        found = {(data["platform"], data["python"]) for data in (json.loads(f.read_text()) for f in files)}
        if len(files) != 12 or found != needed:
            raise AssertionError("Release requires every Linux/Windows/macOS Python 3.11–3.14 pair")


if __name__ == "__main__":
    main()
