"""R packages must remain independent test oracles, never Python runtime code."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_runtime_metadata_contains_no_r_dependency():
    metadata = tomllib.loads((ROOT / "packages/pedgrowth/pyproject.toml").read_text(encoding="utf-8"))
    packages = metadata["project"]["dependencies"]
    assert not packages
    extras = metadata["project"].get("optional-dependencies", {})
    for requirement in [*packages, *(dependency for group in extras.values() for dependency in group)]:
        normalized = requirement.casefold().replace("_", "-")
        assert not normalized.startswith(("rpy2", "rpy-", "rpy-" + "interface"))


def test_r_numerical_references_run_in_dedicated_ci_only():
    workflow = (ROOT / ".github/workflows/official-validation.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    normal = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "r-lib/actions/setup-r@" in workflow
    assert "anthro" in workflow and "anthroplus" in workflow
    assert "cdcanthro" in workflow
    assert "export_intergrowth_gigs_r.R" in workflow
    assert "verify_external_r_snapshots.py" in workflow
    assert "verify_r_validation_licenses.R" in workflow
    assert "verify_who_r_embedded_tables.R" in workflow
    # Numerical R validation remains a separate gated workflow; MIT-only publication
    # must not require unavailable private scientific source fixtures.
    assert "--components core" in release
    assert "official-validation.yml" not in release
    assert "./.github/workflows/official-validation.yml" not in release
    assert "r-lib/actions/setup-r@" not in normal


def test_public_ci_uses_bash_explicitly_on_windows_and_installs_request_types() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "- name: Validate supported Python and platform\n        shell: bash\n        run: |" in ci
    project = tomllib.loads((ROOT / "packages/pedgrowth/pyproject.toml").read_text(encoding="utf-8"))
    assert any(
        requirement.startswith("types-requests")
        for requirement in project["project"]["optional-dependencies"]["dev"]
    )


def test_release_versioner_uses_module_invocation() -> None:
    """Versioning must run from the repository root on clean GitHub runners."""
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert release.count("python -m scripts.auto_version") == 2
    assert "python scripts/auto_version.py" not in release


def test_r_implementations_are_not_part_of_python_runtime_sources():
    package = ROOT / "pedgrowth"
    assert not list(package.rglob("*.R"))
    assert not list(package.rglob("*.r"))
    assert not list(package.rglob("*.RData"))
    assert not list(package.rglob("*.rds"))
