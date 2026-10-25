"""Publication rights are scoped by independently released provider and exact evidence hash."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.verify_reference_rights import (
    PROVIDERS,
    audit_rights,
    check_code_only_publication,
    check_publication_clearance,
    provider_fingerprint,
)


def test_every_reference_has_source_bound_rights_metadata() -> None:
    assert audit_rights() == {"WHO": 24, "CDC": 9, "INTERGROWTH": 7}
    assert len({provider_fingerprint(group) for group in PROVIDERS}) == 4


def test_missing_clearance_blocks_unrestricted_distribution(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="rights clearances"):
        check_publication_clearance(tmp_path / "no_clearance.json")


@pytest.mark.parametrize("family", PROVIDERS)
def test_partial_clearance_blocks_only_the_affected_provider(tmp_path, family) -> None:
    file = tmp_path / "partial.json"
    all_records = {
        item: {
            "status": "cleared",
            "evidence_url": "https://example.org/reviewed-evidence",
            "reviewed_for_release": "1.0.0",
            "reference_manifest_sha256": provider_fingerprint(item),
            "data_license_basis": "For tests only: independently documented rights and approved redistribution.",
        }
        for item in PROVIDERS
    }
    all_records[family]["status"] = "pending"
    file.write_text(
        json.dumps(
            {
                "scope": "unrestricted_public_python_distribution",
                "legal_reviewer": "Responsible Reviewer",
                "providers": all_records,
            }
        )
    )
    with pytest.raises(RuntimeError, match=f"{family} redistribution"):
        check_publication_clearance(file)
    check_publication_clearance(file, providers=tuple(item for item in PROVIDERS if item != family))


def test_clearance_invalid_when_source_inventory_changes(tmp_path) -> None:
    file = tmp_path / "mismatch.json"
    file.write_text(
        json.dumps(
            {
                "scope": "unrestricted_public_python_distribution",
                "legal_reviewer": "Responsible Reviewer",
                "providers": {
                    "cdc": {
                        "status": "cleared",
                        "evidence_url": "https://example.org/reviewed-evidence",
                        "reviewed_for_release": "1.0.0",
                        "reference_manifest_sha256": "0" * 64,
                        "data_license_basis": "For tests only: independently documented rights and approved redistribution.",
                    }
                },
            }
        )
    )
    with pytest.raises(RuntimeError, match="audited reference inventory changed"):
        check_publication_clearance(file, providers=("cdc",))


@pytest.mark.parametrize("family", PROVIDERS)
def test_code_only_provider_publication_does_not_require_redistribution_clearance(family):
    assert not (Path(__file__).resolve().parents[1] / "docs/REFERENCE_PUBLICATION_CLEARANCE.json").exists()
    check_code_only_publication(providers=(family,))


def test_code_only_publication_rejects_coefficient_files_and_false_metadata(tmp_path, monkeypatch):
    import shutil

    from scripts import verify_reference_rights as rights

    root = Path(__file__).resolve().parents[1]
    original = root / "packages/pedgrowth-data-cdc"
    copy = tmp_path / "packages/pedgrowth-data-cdc"
    shutil.copytree(original, copy)
    monkeypatch.setattr(rights, "ROOT", tmp_path)

    data = copy / "src/pedgrowth/data/cdc/data"
    (data / "leaked.lmsb").write_bytes(b"not a scientific coefficient")
    with pytest.raises(RuntimeError, match="embedded"):
        check_code_only_publication(providers=("cdc",))
    (data / "leaked.lmsb").unlink()

    rights_json = data / "SOURCE_RIGHTS.json"
    raw = json.loads(rights_json.read_text())
    raw["source_form_in_data_distribution"] = True
    rights_json.write_text(json.dumps(raw))
    with pytest.raises(RuntimeError, match="bundled scientific data"):
        check_code_only_publication(providers=("cdc",))


def test_code_only_publication_rejects_unexpected_json_resources(tmp_path, monkeypatch):
    import shutil

    from scripts import verify_reference_rights as rights

    package = tmp_path / "packages/pedgrowth-data-intergrowth"
    shutil.copytree(Path(__file__).resolve().parents[1] / "packages/pedgrowth-data-intergrowth", package)
    monkeypatch.setattr(rights, "ROOT", tmp_path)

    resource = package / "src/pedgrowth/data/intergrowth/data/disguised_coefficients.json"
    resource.write_text('{"parameters": [1, 2, 3]}')
    with pytest.raises(RuntimeError, match="unexpected embedded package data resource"):
        check_code_only_publication(providers=("intergrowth",))


@pytest.mark.parametrize(
    "invocation", (("-m", "scripts.verify_reference_rights"), ("scripts/verify_reference_rights.py",))
)
def test_release_rights_validator_cli_imports_sibling_modules(invocation: tuple[str, ...]) -> None:
    """Exercise GitHub and documented direct CLI entry points in a fresh subprocess."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(  # noqa: S603 - fixed Python executable and trusted CLI arguments
        [sys.executable, *invocation, "--enforce-publication", "--providers", "intergrowth"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Code-only provider publication checks passed" in result.stdout


def test_data_redistribution_still_requires_real_clearance(tmp_path):
    with pytest.raises(RuntimeError, match="rights clearances"):
        check_publication_clearance(tmp_path / "missing.json", providers=("who2006",))
