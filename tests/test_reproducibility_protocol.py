"""Ensure cross-platform reference identifiers and z-score gate fail closed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.compare_reproducibility import compare


def evidence(path: Path, os: str, version: str, z: float = 0.125, ref: str = "WHO") -> Path:
    path.write_text(
        json.dumps(
            {
                "platform": os,
                "python": version,
                "observations": {"case": {"z": z, "reference_id": ref}},
            }
        )
    )
    return path


def test_accepts_rounding_only(tmp_path):
    a = evidence(tmp_path / "a.json", "Linux", "3.11")
    b = evidence(tmp_path / "b.json", "Windows", "3.12", 0.12500000000001)
    assert compare([a, b])["environment_count"] == 2


def test_rejects_reference_selection_change(tmp_path):
    a = evidence(tmp_path / "a.json", "Linux", "3.11")
    b = evidence(tmp_path / "b.json", "Windows", "3.12", ref="CDC")
    with pytest.raises(AssertionError, match="Different references"):
        compare([a, b])


def test_rejects_numerical_drift(tmp_path):
    a = evidence(tmp_path / "a.json", "Linux", "3.11")
    b = evidence(tmp_path / "b.json", "Windows", "3.12", 0.130)
    with pytest.raises(AssertionError, match="Different z-score"):
        compare([a, b])


def test_rejects_duplicate_or_missing_version(tmp_path):
    a = evidence(tmp_path / "a.json", "Linux", "3.11")
    b = evidence(tmp_path / "b.json", "Linux", "3.11")
    with pytest.raises(AssertionError, match="Duplicate"):
        compare([a, b])
    c = evidence(tmp_path / "c.json", "Darwin", "3.13")
    with pytest.raises(AssertionError, match="Missing interpreters"):
        compare([a, c], expected_versions={"3.11", "3.12", "3.13"})
