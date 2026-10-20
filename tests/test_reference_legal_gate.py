"""Publication rights are scoped by independently released provider and exact evidence hash."""

from __future__ import annotations

import json

import pytest

from scripts.verify_reference_rights import (
    PROVIDERS,
    audit_rights,
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
