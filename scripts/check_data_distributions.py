"""Verify each native reference plugin wheel and source archive independently."""

from __future__ import annotations

import argparse
import json
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("who2006", "who2007", "cdc", "intergrowth")


def _allowed_provider_data_files(group: str) -> set[str]:
    """A code-only distribution carries provenance metadata, never numerical tables."""
    names = {"SOURCE_RIGHTS.json", "SOURCE_LICENSE_MATRIX.json"}
    if group == "intergrowth":
        names |= {"INTERGROWTH_SOURCES.json", "__init__.py"}
    else:
        names.add("SOURCES.json")
    return names


def _check_data_tree(names: set[str], *, prefix: str, group: str) -> None:
    data_prefix = prefix + "data/"
    unexpected = sorted(
        name
        for name in names
        if name.startswith(data_prefix)
        and name[len(data_prefix) :] not in _allowed_provider_data_files(group)
    )
    if unexpected:
        raise ValueError(
            f"{group} code-only distribution contains non-metadata scientific data files: {unexpected}"
        )


def _sources() -> dict[str, Any]:
    return cast(
        dict[str, Any], json.loads((ROOT / "validation/source_data/SOURCES.json").read_text())["tables"]
    )


def _tables(group: str) -> dict[str, dict[str, Any]]:
    return {
        name: info
        for name, info in _sources().items()
        if (
            name.startswith("who_")
            if group == "who2006"
            else name.startswith("who2007_")
            if group == "who2007"
            else name.startswith("cdc_")
            if group == "cdc"
            else False
        )
    }


def check_wheel(path: Path, group: str) -> dict[str, Any]:
    module = "pedgrowth.data." + group
    prefix = "pedgrowth/data/" + group + "/"
    stem = "pedgrowth_data_" + group
    if not path.name.startswith(stem + "-"):
        raise ValueError("Incorrect reference provider wheel")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if any(
            (p.startswith("pedgrowth/") and not p.startswith(prefix)) or p.startswith("tests/") for p in names
        ):
            raise ValueError("Reference wheel may not contain core or test modules")
        required = {
            prefix + "__init__.py",
            prefix + "data/SOURCE_RIGHTS.json",
            prefix + "data/SOURCE_LICENSE_MATRIX.json",
        }
        if not required <= names:
            raise ValueError("Reference provider missing source-specific rights documents")
        if "pedgrowth/__init__.py" in names or "pedgrowth/data/__init__.py" in names:
            raise ValueError("An extension must not overwrite the shared pedgrowth namespace root")
        rights = json.loads(archive.read(prefix + "data/SOURCE_RIGHTS.json"))
        audit = json.loads(archive.read(prefix + "data/SOURCE_LICENSE_MATRIX.json"))
        scientific = _tables(group)
        expected_names = (
            set(scientific)
            if group != "intergrowth"
            else {
                "intergrowth_preterm_postnatal_weight",
                "intergrowth_preterm_postnatal_length",
                "intergrowth_preterm_postnatal_head_circumference",
                "intergrowth_preterm_postnatal_weight_for_length",
                "intergrowth_very_preterm_birth_weight",
                "intergrowth_very_preterm_birth_length",
                "intergrowth_very_preterm_birth_head_circumference",
            }
        )
        if set(audit) != expected_names:
            raise ValueError("Source-specific rights matrix lacks reference coverage")
        restricted = [
            item
            for item in names
            if item.startswith(prefix)
            and (
                item.lower().endswith((".csv", ".lmsb", ".xlsx", ".xls", ".rds", ".rdata"))
                or "/source_tables/" in item
                or item.endswith("/intergrowth_coefficients.json")
            )
        ]
        if restricted:
            raise ValueError(f"Reference coefficient values shipped in {group} wheel: {restricted}")
        _check_data_tree(names, prefix=prefix, group=group)
        if prefix + "downloader.py" not in names:
            raise ValueError(f"Provider {group} wheel lacks the verified downloader")
        entries = [n for n in names if n.endswith(".dist-info/entry_points.txt")]
        if len(entries) != 1 or f"{group} = {module}:register" not in archive.read(entries[0]).decode():
            raise ValueError("Missing or incorrect extension registration entry point")
        path_meta = next(n for n in names if n.endswith(".dist-info/METADATA"))
        metadata = BytesParser().parsebytes(archive.read(path_meta))
        if metadata["Name"] != "pedgrowth-data-" + group:
            raise ValueError("Wrong wheel project identity")
        if metadata["License-Expression"] != rights["packaging_code_license_expression"]:
            raise ValueError(f"{group}: installed code license does not match provider rights metadata")
        if "pedgrowth==" + metadata["Version"] not in metadata.get_all("Requires-Dist", []):
            raise ValueError("Provider must depend on the matching core version")
        if not any(n.endswith(".dist-info/licenses/SOURCE_RIGHTS.md") for n in names):
            raise ValueError("Source license rights notice is missing")
        return {
            "local_validation_only": (prefix + "data/LOCAL_QA_ONLY.json") in names,
            "license_expression": rights.get("license_expression"),
            "files": {n: v for n, v in scientific.items()}
            if scientific
            else {"intergrowth_coefficients.json": {}},
            "r_package": rights["r_package"],
            "validation": rights["validation"],
            "packaging_code_license_expression": rights["packaging_code_license_expression"],
            "r_program_license_is_data_redistribution_grant": rights[
                "r_program_license_is_data_redistribution_grant"
            ],
            "official_reference_pages": rights["official_reference_pages"],
            "scientific_values_origin": rights["scientific_values_origin"],
        }


def check_sdist(path: Path, group: str, version: str) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = {p.name for p in archive.getmembers() if p.isfile()}
        prefix = "pedgrowth_data_" + group + "-" + version + "/"
        required = {
            prefix + "pyproject.toml",
            prefix + "README.md",
            prefix + "SOURCE_RIGHTS.md",
            prefix + "src/pedgrowth/data/" + group + "/__init__.py",
            prefix + "src/pedgrowth/data/" + group + "/data/SOURCE_LICENSE_MATRIX.json",
        }
        if not required <= names:
            raise ValueError("Independent provider sdist misses its source tree or rights")
        if any(
            "/tests/" in f
            or (
                f.startswith(prefix + "src/pedgrowth/")
                and not f.startswith(prefix + "src/pedgrowth/data/" + group + "/")
            )
            for f in names
        ):
            raise ValueError("Scientific provider source archive must not bundle tests or core")
        restricted = [
            file
            for file in names
            if file.startswith(prefix)
            and (
                file.lower().endswith((".csv", ".lmsb", ".xlsx", ".xls", ".rds", ".rdata"))
                or "/source_tables/" in file
                or file.endswith("/intergrowth_coefficients.json")
            )
        ]
        if restricted:
            raise ValueError(f"Reference coefficient data in {group} source distribution")
        _check_data_tree(
            names,
            prefix=prefix + "src/pedgrowth/data/" + group + "/",
            group=group,
        )
        if prefix + "src/pedgrowth/data/" + group + "/downloader.py" not in names:
            raise ValueError("Provider sdist missing verified source downloader")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    for group in GROUPS:
        stem = "pedgrowth_data_" + group
        wheels = list(args.directory.glob(stem + "-*.whl"))
        sdists = list(args.directory.glob(stem + "-*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            raise ValueError(f"Expected exactly one wheel and sdist for {group}")
        check_wheel(wheels[0], group)
        name = sdists[0].name
        version = name.removeprefix(stem + "-").removesuffix(".tar.gz")
        check_sdist(sdists[0], group, version)
        print(f"Verified independently packaged {group} provider")
    print("All four native reference extensions passed scientific and packaging integrity checks.")


if __name__ == "__main__":
    main()
