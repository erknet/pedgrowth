"""Pedgrowth distribution identity and absence of the unrelated PyPI namespace."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pedgrowth as public
from pedgrowth import AgeDefinition, AgeType, AgeUnit
from pedgrowth.data.cdc import CdcClinicalPlan
from pedgrowth.registry import available_plans

ROOT = Path(__file__).resolve().parents[1]


def test_pedgrowth_public_api_is_available():
    assert public.__version__ == "1.0.0"
    assert "GrowthChartsCalculator" in public.__all__
    assert "IntergrowthPlan" not in public.__all__
    assert "intergrowth" in available_plans()
    assert public.GrowthChartsCalculator is not None
    assert CdcClinicalPlan is not None


def test_pedgrowth_can_select_official_reference():
    age = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)
    calculator = public.GrowthChartsCalculator(plan=CdcClinicalPlan())
    for months, expected in ((12, "who"), (23.99, "who"), (24, "cdc"), (36, "cdc")):
        result = calculator.calculate(
            indicator="wfa",
            sex="M",
            age=months,
            age_definition=age,
            measurement=11.4,
        )
        assert result.reference_id.startswith(expected)


def test_distribution_is_only_pedgrowth_to_avoid_pypi_conflict():
    project = tomllib.loads((ROOT / "packages/pedgrowth/pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["name"] == "pedgrowth"
    assert project["project"]["dependencies"] == []
    assert project["project"]["license"] == "MIT"
    assert project["tool"]["setuptools"]["packages"]["find"]["include"] == ["pedgrowth*"]
    assert (ROOT / "packages/pedgrowth/src/pedgrowth/py.typed").is_file()
    assert (ROOT / "validation/source_data/SOURCES.json").is_file()
    assert not (ROOT / "growthcharts").exists()


def test_release_wiring_keeps_redistribution_permission_gate():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    for necessary in (
        "https://pypi.org/project/pedgrowth/",
        "pedgrowth-release-distributions",
        "scripts/build_distributions.py --mode publication --components core",
    ):
        assert necessary in workflow
    provider_workflow = (ROOT / ".github/workflows/provider-release.yml").read_text(encoding="utf-8")
    assert "--enforce-publication --providers" in provider_workflow
    assert '--components "$PROVIDER"' in provider_workflow
    assert "https://pypi.org/project/growthcharts/" not in workflow
    assert "growthcharts-release-distributions" not in workflow


def test_r_validation_script_checks_all_upstream_gpl_licenses():
    source = (ROOT / "scripts/verify_r_validation_licenses.R").read_text(encoding="utf-8")
    for name in ("anthro", "anthroplus", "cdcanthro", "gigs"):
        assert name in source
    assert "GPL-3" in source
    assert "GPL (>= 3)" in source
    workflow = (ROOT / ".github/workflows/official-validation.yml").read_text(encoding="utf-8")
    assert workflow.count("scripts/verify_r_validation_licenses.R") == 2
    assert "scripts/export_intergrowth_gigs_r.R" in workflow
