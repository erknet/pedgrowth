"""Test the external CSV comparison harness without requiring a local R installation.

These tests check the harness behavior; they are NOT replacements for the
independent WHO/CDC R computation executed by official-validation.yml.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.validate_official import compare


def _write(path: Path, count: int, *, unexpected: float = -5.04) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        out = csv.writer(stream)
        out.writerow(["standard", "indicator", "age", "sex", "measurement", "expected"])
        for _ in range(count):
            # From the WHO anthroplus independently published R README example.
            out.writerow(["who", "hfa", 100, "M", 100, unexpected])


def test_independent_validation_csv_harness_accepts_reported_who_precision(tmp_path: Path) -> None:
    csv_file = tmp_path / "official.csv"
    _write(csv_file, 86)
    count, largest = compare(csv_file)
    assert count == 86
    assert 0 <= largest < 0.03


def test_independent_validation_csv_harness_fails_on_discrepancy(tmp_path: Path) -> None:
    csv_file = tmp_path / "official.csv"
    _write(csv_file, 86, unexpected=-4.0)
    with pytest.raises(AssertionError, match="86/86"):
        compare(csv_file)


def test_independent_validation_requires_sufficient_external_cases(tmp_path: Path) -> None:
    csv_file = tmp_path / "official.csv"
    _write(csv_file, 4)
    with pytest.raises(RuntimeError, match="unexpectedly small"):
        compare(csv_file)
