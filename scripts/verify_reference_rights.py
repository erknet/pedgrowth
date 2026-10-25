"""Audit reference rights and distinguish code-only releases from data redistribution.

Publication of extensions WITHOUT scientific numerical data must verify
their source metadata, attribution, code licenses and package-data exclusions.
Signed third-party DATA redistribution approvals remain a separate, explicit
gate if scientific coefficients are ever bundled. No automated check grants
permission to download or use upstream reference data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# GitHub Actions and documented CLI usage may invoke this as a file.
# Add the repository root so sibling modules import identically in both modes.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RIGHTS = ROOT / "docs/REFERENCE_REUSE_RIGHTS.json"
SOURCE = ROOT / "validation/source_data/SOURCES.json"
CLEARANCE = ROOT / "docs/REFERENCE_PUBLICATION_CLEARANCE.json"
LICENSE_MATRIX = ROOT / "docs/REFERENCE_LICENSE_MATRIX.json"
PROVIDERS = ("who2006", "who2007", "cdc", "intergrowth")


def provider_fingerprint(family: str) -> str:
    """Fingerprint the exact table-level evidence that a reviewer approves."""
    if family not in PROVIDERS:
        raise ValueError(f"Unknown provider: {family}")
    rows = json.loads(LICENSE_MATRIX.read_text(encoding="utf-8"))["references"]
    subset = {name: record for name, record in rows.items() if record["family"] == family}
    if len(subset) != (
        18 if family == "who2006" else 6 if family == "who2007" else 9 if family == "cdc" else 7
    ):
        raise RuntimeError(f"Invalid {family} rights reference inventory")
    return hashlib.sha256(json.dumps(subset, sort_keys=True).encode("utf-8")).hexdigest()


def audit_rights() -> dict[str, int]:
    policy = json.loads(RIGHTS.read_text())
    source = json.loads(SOURCE.read_text())["tables"]
    entries = policy["source_data"]
    if set(source) != set(entries):
        raise RuntimeError(f"Rights coverage mismatch: {set(source) ^ set(entries)}")
    for name, meta in source.items():
        item = entries[name]
        for field, mapped in (
            ("standard", "standard"),
            ("reference_version", "reference_version"),
            ("source_url", "upstream_url"),
            ("source_sha256", "upstream_sha256"),
            ("csv_sha256", "normalized_sha256"),
        ):
            if meta[field] != item[mapped]:
                raise RuntimeError(f"{name}: reference rights provenance drift: {field}")
        if item["redistribution_status"] not in (
            "unresolved_for_unrestricted_public_redistribution",
            "cdc_public_domain_reuse_subject_to_attribution_exceptions",
        ):
            raise RuntimeError(f"{name}: unknown rights status")
        if not item["rights_basis_url"].startswith("https://"):
            raise RuntimeError(f"{name}: missing official rights source")
    who_count = sum(item["standard"] == "WHO" for item in entries.values())
    cdc_count = sum(item["standard"] == "CDC" for item in entries.values())
    if (who_count, cdc_count) != (24, 9):
        raise RuntimeError("Unexpected WHO/CDC rights source counts")
    if policy["intergrowth_equations"]["count"] != 7:
        raise RuntimeError("Missing INTERGROWTH rights inventory")
    matrix = json.loads(LICENSE_MATRIX.read_text(encoding="utf-8"))
    if matrix.get("schema_version") != 1 or set(matrix["references"]) != (
        set(source)
        | {
            "intergrowth_preterm_postnatal_weight",
            "intergrowth_preterm_postnatal_length",
            "intergrowth_preterm_postnatal_head_circumference",
            "intergrowth_preterm_postnatal_weight_for_length",
            "intergrowth_very_preterm_birth_weight",
            "intergrowth_very_preterm_birth_length",
            "intergrowth_very_preterm_birth_head_circumference",
        }
    ):
        raise RuntimeError("Reference-level licensing matrix does not cover all 40 models")
    for name, entry in matrix["references"].items():
        if name in source:
            original = source[name]
            if (
                entry["source_sha256"] != original["source_sha256"]
                or entry["normalized_sha256"] != original["csv_sha256"]
            ):
                raise RuntimeError(f"{name}: licensing evidence no longer matches pinned source")
            if entry["family"] not in PROVIDERS:
                raise RuntimeError("Invalid rights source family")
        if entry.get("license_review_status") != "pending":
            raise RuntimeError("Technical inventory must not impersonate a human permission grant")
    for family in PROVIDERS:
        provider_fingerprint(family)
    entries = matrix["references"]
    if sum(int(x.get("r_domain_extra_rows", 0)) for x in entries.values()) != 420:
        raise RuntimeError("WHO 2006 website-only coverage exception no longer matches reviewed data")
    exceptions = [x for x in entries.values() if x["family"] == "who2006" and x.get("r_domain_extra_rows", 0)]
    if len(exceptions) != 14 or any(x["r_domain_extra_rows"] != 30 for x in exceptions):
        raise RuntimeError("The additional WHO daily records lack exact source coverage")
    if sum(int(x.get("r_embedded_matching_rows") or 0) for x in entries.values()) != 28228:
        raise RuntimeError("WHO-authored R coefficient match totals drifted")
    intergrowth = json.loads((ROOT / "validation/source_data/INTERGROWTH_SOURCES.json").read_text())
    for entry in entries.values():
        if entry["family"] == "intergrowth" and entry["source_sha256"] != intergrowth["sha256"]:
            raise RuntimeError("INTERGROWTH coefficients differ from the audited original source")
    return {"WHO": who_count, "CDC": cdc_count, "INTERGROWTH": 7}


def check_code_only_publication(*, providers: tuple[str, ...] = PROVIDERS) -> None:
    """Reject provider source that would redistribute scientific coefficients.

    This technical distribution check makes no legal assertion about access
    or use of reference data fetched separately by downstream users.
    """
    for family in providers:
        if family not in PROVIDERS:
            raise RuntimeError(f"Invalid publication target: {family}")
        package = ROOT / "packages" / ("pedgrowth-data-" + family)
        module = package / "src" / "pedgrowth" / "data" / family
        data = module / "data"
        rights = json.loads((data / "SOURCE_RIGHTS.json").read_text())
        project = tomllib.loads((package / "pyproject.toml").read_text())["project"]
        code_license = rights.get("packaging_code_license_expression")
        if not isinstance(code_license, str) or project.get("license") != code_license:
            raise RuntimeError(f"{family}: independent Python code license metadata mismatch")
        if "LICENSE" not in project.get("license-files", []) or not (package / "LICENSE").is_file():
            raise RuntimeError(f"{family}: missing code license text")
        notice = package / "SOURCE_RIGHTS.md"
        if "SOURCE_RIGHTS.md" not in project["license-files"] or not notice.is_file():
            raise RuntimeError(f"{family}: missing original-source attribution and terms notice")
        content = notice.read_text()
        if not all(word in content.lower() for word in ("code", "source", "not", "license")):
            raise RuntimeError(f"{family}: source-rights notice omits its licensing boundary")
        if (
            rights.get("source_form_in_data_distribution") is not False
            or rights.get("installed_by_default") is not False
        ):
            raise RuntimeError(f"{family}: provider metadata wrongly claims bundled scientific data")
        if rights.get("source_use_terms_review_status") != "pending_source_specific_review":
            raise RuntimeError(f"{family}: unreviewed upstream terms must be stated accurately")
        if not rights.get("official_reference_pages") or not all(
            str(item.get("url", "")).startswith("https://") for item in rights["official_reference_pages"]
        ):
            raise RuntimeError(f"{family}: incomplete authoritative source provenance")
        for required in ("downloader.py", "__init__.py"):
            if not (module / required).is_file():
                raise RuntimeError(f"{family}: missing source code acquisition component {required}")
        if (data / "LOCAL_QA_ONLY.json").exists():
            raise RuntimeError(f"{family}: outdated research-only publication marker remains")
        if family == "intergrowth":
            required_manifest = data / "INTERGROWTH_SOURCES.json"
        else:
            required_manifest = data / "SOURCES.json"
        if not required_manifest.is_file() or not (data / "SOURCE_LICENSE_MATRIX.json").is_file():
            raise RuntimeError(f"{family}: missing audited provenance manifest")
        manifest_in = (package / "MANIFEST.in").read_text()
        if family == "intergrowth":
            if "intergrowth_coefficients.json" not in manifest_in:
                raise RuntimeError(f"{family}: sdist must exclude reconstructed coefficient JSON")
        elif "recursive-exclude" not in manifest_in or "prune " not in manifest_in:
            raise RuntimeError(f"{family}: sdist must exclude source and compiled coefficients")
        # Match the strict wheel/sdist data-file allowlist, including files with
        # disguised extensions. A code-only release may ship manifests, not
        # arbitrary resources or numerical tables under the package data tree.
        from scripts.check_data_distributions import _allowed_provider_data_files

        allowed = _allowed_provider_data_files(family)
        for source in data.rglob("*"):
            if source.is_file() and source.relative_to(data).as_posix() not in allowed:
                raise RuntimeError(f"{family}: unexpected embedded package data resource: {source.name}")


def check_publication_clearance(path: Path = CLEARANCE, *, providers: tuple[str, ...] = PROVIDERS) -> None:
    if not path.is_file():
        raise RuntimeError(
            "Public release blocked: source-specific rights clearances have not been signed. "
            "See THIRD_PARTY_NOTICES.md and docs/REFERENCE_REUSE_RIGHTS.json."
        )
    approval: dict[str, Any] = json.loads(path.read_text())
    if approval.get("scope") != "unrestricted_public_python_distribution":
        raise RuntimeError("Release clearance must explicitly cover unrestricted public Python distribution")
    if not isinstance(approval.get("legal_reviewer"), str) or len(approval["legal_reviewer"].strip()) < 5:
        raise RuntimeError("A named accountable legal reviewer must sign off")
    for family in providers:
        if family not in PROVIDERS:
            raise RuntimeError(f"Invalid clearance target: {family}")
        record = approval.get("providers", {}).get(family, {})
        if record.get("status") != "cleared":
            raise RuntimeError(f"Publication blocked: {family} redistribution clearance missing")
        evidence = record.get("evidence_url")
        if not isinstance(evidence, str) or not evidence.startswith("https://"):
            raise RuntimeError(f"Publication blocked: {family} clearance needs reviewable evidence")
        if not isinstance(record.get("reviewed_for_release"), str) or not record["reviewed_for_release"]:
            raise RuntimeError(f"Publication blocked: {family} release scope must be confirmed")
        if record.get("reference_manifest_sha256") != provider_fingerprint(family):
            raise RuntimeError(f"Publication blocked: {family} audited reference inventory changed")
        if (
            not isinstance(record.get("data_license_basis"), str)
            or len(record["data_license_basis"].strip()) < 30
        ):
            raise RuntimeError(
                f"Publication blocked: {family} must state explicit numerical data reuse basis"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--enforce-publication",
        action="store_true",
        help="Check code-only publication requirements (does not grant upstream data rights)",
    )
    parser.add_argument(
        "--enforce-data-redistribution",
        action="store_true",
        help="Require signed human clearance before bundling numerical data",
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        choices=PROVIDERS,
        default=list(PROVIDERS),
        help="Only check the selected data provider(s); default: all four",
    )
    args = parser.parse_args()
    counts = audit_rights()
    print("Complete provenance/rights inventory:", counts)
    if args.enforce_publication:
        check_code_only_publication(providers=tuple(args.providers))
        print("Code-only provider publication checks passed; upstream access/use terms remain independent.")
    if args.enforce_data_redistribution:
        check_publication_clearance(providers=tuple(args.providers))
        print("Signed data redistribution clearance records satisfy the separate data gate")
    if not args.enforce_publication and not args.enforce_data_redistribution:
        print("Audit only — this does not authorize scientific data redistribution or use.")


if __name__ == "__main__":
    main()
