"""Build five native Python projects from the pedgrowth monorepo.

Each project owns a persistent package directory and an independent
pyproject.toml. No temporary Python packages or copied source code.
Publication is rejected for uncleared scientific providers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA = ROOT / "validation" / "source_data"
GROUPS = ("who2006", "who2007", "cdc", "intergrowth")
DISTRIBUTIONS = {"core": "pedgrowth", **{g: f"pedgrowth-data-{g}" for g in GROUPS}}
SOURCE_MODULES = {g: "pedgrowth.data." + g for g in GROUPS}


def _version() -> str:
    return str(tomllib.loads((ROOT / "packages/pedgrowth/pyproject.toml").read_text())["project"]["version"])


def _sources() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((DATA / "SOURCES.json").read_text())["tables"])


def _group_table_names(group: str, sources: dict[str, Any]) -> list[str]:
    if group == "who2006":
        return sorted(name for name in sources if name.startswith("who_"))
    if group == "who2007":
        return sorted(name for name in sources if name.startswith("who2007_"))
    if group == "cdc":
        return sorted(name for name in sources if name.startswith("cdc_"))
    raise ValueError(f"Unknown tabulated provider: {group}")


def _check_package_sources(group: str) -> None:
    from pedgrowth.compiled import encode_csv

    module = SOURCE_MODULES[group]
    data = ROOT / "packages" / DISTRIBUTIONS[group] / "src" / Path(*module.split(".")) / "data"
    reference_matrix = json.loads((ROOT / "docs/REFERENCE_LICENSE_MATRIX.json").read_text())["references"]
    rights = json.loads((data / "SOURCE_RIGHTS.json").read_text())
    if rights.get("expected_reference_count") != (
        1 if group == "intergrowth" else len(_group_table_names(group, _sources()))
    ):
        raise RuntimeError(f"{group}: wrong reference source count")
    local_matrix = json.loads((data / "SOURCE_LICENSE_MATRIX.json").read_text())
    expected_matrix = {name: row for name, row in reference_matrix.items() if row["family"] == group}
    if local_matrix != expected_matrix:
        raise RuntimeError(f"{group}: package licensing matrix differs from the reviewed audit")
    if group == "intergrowth":
        manifest = json.loads((data / "INTERGROWTH_SOURCES.json").read_text())
        source = data / "intergrowth_coefficients.json"
        if source.exists() and hashlib.sha256(source.read_bytes()).hexdigest() != manifest["sha256"]:
            raise RuntimeError("INTERGROWTH local research coefficient snapshot has changed")
        return
    sources = _sources()
    for name in _group_table_names(group, sources):
        item = sources[name]
        source_file = data / "source_tables" / (name + ".csv")
        compiled_file = data / (name + ".lmsb")
        if not source_file.exists() and not compiled_file.exists():
            continue  # Data downloaded by end users; do not require private snapshots.
        if source_file.exists() != compiled_file.exists():
            raise RuntimeError(f"{name}: incomplete private research fixture pair")
        csv = source_file.read_bytes()
        lmsb = compiled_file.read_bytes()
        if hashlib.sha256(csv).hexdigest() != item["csv_sha256"]:
            raise RuntimeError(f"{name}: normalized source CSV hash mismatch")
        if hashlib.sha256(lmsb).hexdigest() != item["lmsb_sha256"] or encode_csv(csv) != lmsb:
            raise RuntimeError(f"{name}: packed LMS binary differs from editable source")


def _assert_release_clearance(group: str, version: str) -> None:
    from scripts.verify_reference_rights import check_publication_clearance

    check_publication_clearance(providers=(group,))
    package = ROOT / "packages" / DISTRIBUTIONS[group]
    src = package / "src" / Path(*SOURCE_MODULES[group].split(".")) / "data"
    rights = json.loads((src / "SOURCE_RIGHTS.json").read_text())
    if (
        rights.get("rights_status") != "cleared_for_publication"
        or not isinstance(rights.get("license_expression"), str)
        or not rights["license_expression"]
        or not isinstance(rights.get("evidence_url"), str)
        or not rights["evidence_url"].startswith("https://")
    ):
        raise RuntimeError(f"{group}: provider numeric-data licensing not yet approved")
    if (src / "LOCAL_QA_ONLY.json").exists():
        raise RuntimeError(f"{group}: unreleased research-only marker remains")
    if not (package / "SOURCE_LICENSE.md").is_file():
        raise RuntimeError(f"{group}: human-approved data rights document is missing")
    project = tomllib.loads((package / "pyproject.toml").read_text())["project"]
    if project["version"] != version:
        raise RuntimeError(f"{group}: distribution version does not match core")
    if (
        project.get("license") is not None
        and project["license"] != rights["packaging_code_license_expression"]
    ):
        raise RuntimeError(f"{group}: code license metadata does not match code rights")
    # Source-data rights are independent of the code license: see
    # rights["license_expression"] and the signed provider clearance.


def build_all(*, mode: str, output: Path, components: tuple[str, ...]) -> list[Path]:
    if (
        mode not in ("local", "publication")
        or not components
        or any(c not in DISTRIBUTIONS for c in components)
    ):
        raise ValueError("Unknown build mode or components")
    version = _version()
    output = output.resolve()
    if mode == "local" and output == (ROOT / "dist").resolve():
        raise RuntimeError("Local scientific packages cannot be written into release dist/")
    if mode == "publication" and (output / "NOT_FOR_PUBLIC_DISTRIBUTION.txt").exists():
        raise RuntimeError("Cannot mix unpublished research artifacts with publication")
    for group in components:
        project = ROOT / "packages" / DISTRIBUTIONS[group]
        declared = str(tomllib.loads((project / "pyproject.toml").read_text())["project"]["version"])
        if declared != version:
            raise RuntimeError(f"{group}: version mismatch {declared} != {version}")
        if group != "core":
            _check_package_sources(group)
            if mode == "publication":
                _assert_release_clearance(group, version)
    output.mkdir(parents=True, exist_ok=True)
    results: list[Path] = []
    for group in components:
        project = ROOT / "packages" / DISTRIBUTIONS[group]
        subprocess.run(  # noqa: S603 - sys.executable invoking the audited local Python build module
            [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output), str(project)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        prefix = DISTRIBUTIONS[group].replace("-", "_") + "-" + version
        selected = sorted(
            f
            for f in output.iterdir()
            if f.name.startswith(prefix) and (f.suffix == ".whl" or f.name.endswith(".tar.gz"))
        )
        if len(selected) != 2:
            raise RuntimeError(f"Expected one wheel and one source archive for {group}: {selected}")
        results.extend(selected)
        print(f"Built native package {DISTRIBUTIONS[group]}: {[p.name for p in selected]}")
    if mode == "local" and any(c != "core" for c in components):
        (output / "NOT_FOR_PUBLIC_DISTRIBUTION.txt").write_text(
            "PRIVATE RESEARCH ONLY. Scientific source redistribution rights are not cleared.\n"
        )
    (output / "BUILD_MANIFEST.json").write_text(
        json.dumps(
            {
                "mode": mode,
                "version": version,
                "contents": [
                    {"artifact": f.name, "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
                    for f in results
                ],
            },
            indent=2,
        )
        + "\n"
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["local", "publication"], default="local")
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".local" / "split-distributions")
    parser.add_argument("--components", nargs="+", choices=tuple(DISTRIBUTIONS), default=tuple(DISTRIBUTIONS))
    args = parser.parse_args()
    build_all(mode=args.mode, output=args.output_dir, components=tuple(args.components))


if __name__ == "__main__":
    main()
