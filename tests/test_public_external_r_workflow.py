"""Offline guards for the public code-only independent R validation pipeline."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.prepare_live_who_r_audit import prepare


def test_who_audit_refuses_to_export_scientific_tables_into_the_git_tree(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="under .local"):
        prepare(tmp_path / "reference-tables")


def test_intergrowth_public_challenge_generator_has_full_synthetic_coverage(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    destination = tmp_path / "independent-inputs.csv"
    result = subprocess.run(  # noqa: S603 - trusted interpreter and checked-in source script
        [sys.executable, str(root / "scripts/prepare_intergrowth_r_challenges.py"), str(destination)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    with destination.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 4970
    assert {(row["family"], row["indicator"], row["sex"]) for row in rows} == {
        (family, indicator, sex)
        for family, indicators in {
            "preterm_postnatal": ("weight", "length", "head_circumference", "weight_for_length"),
            "very_preterm_birth": ("weight", "length", "head_circumference"),
        }.items()
        for indicator in indicators
        for sex in ("M", "F")
    }
    assert all(row["scenario"] in {"boundary", "random", "extreme"} for row in rows)
