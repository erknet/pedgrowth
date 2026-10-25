"""Monorepo split distribution, optional extras and source licensing boundaries."""

from __future__ import annotations

import io
import json
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

from scripts.build_distributions import GROUPS, _group_table_names, _sources, build_all
from scripts.check_data_distributions import check_sdist, check_wheel

ROOT = Path(__file__).resolve().parents[1]


def test_source_data_is_retained_in_monorepo_and_mapped_to_four_packages():
    origin = ROOT / "validation" / "source_data"
    sources = _sources()
    assert len(sources) == 33
    assert set(GROUPS) == {"who2006", "who2007", "cdc", "intergrowth"}
    assert len(_group_table_names("who2006", sources)) == 18
    assert len(_group_table_names("who2007", sources)) == 6
    assert len(_group_table_names("cdc", sources)) == 9
    for key, info in sources.items():
        # Private research checkouts may contain the original scientific CSV.
        # The code-only public checkout only carries verified source hashes.
        scientific = origin / (key + ".csv")
        if scientific.is_file():
            import hashlib

            assert hashlib.sha256(scientific.read_bytes()).hexdigest() == info["csv_sha256"]
        assert len(info["lmsb_sha256"]) == 64
    assert (origin / "INTERGROWTH_SOURCES.json").is_file()


def test_version_locked_core_extras_address_the_correct_provider_distributions():
    with (ROOT / "packages/pedgrowth/pyproject.toml").open("rb") as stream:
        info = tomllib.load(stream)["project"]
    version = info["version"]
    dependencies = info["optional-dependencies"]
    mapped = {
        "who2006": ("pedgrowth-data-who2006",),
        "who2007": ("pedgrowth-data-who2007",),
        "who": ("pedgrowth-data-who2006", "pedgrowth-data-who2007"),
        "cdc": ("pedgrowth-data-cdc",),
        "intergrowth": ("pedgrowth-data-intergrowth",),
        "all": (
            "pedgrowth-data-who2006",
            "pedgrowth-data-who2007",
            "pedgrowth-data-cdc",
            "pedgrowth-data-intergrowth",
        ),
    }
    for extra, distributions in mapped.items():
        assert dependencies[extra] == [name + "==" + version for name in distributions]
    assert info["license"] == "MIT"
    assert not info["dependencies"]


def test_cdc_build_is_independent_code_only_wheel(tmp_path: Path):
    pytest.importorskip("build")
    pytest.importorskip("wheel")
    pytest.importorskip("setuptools")
    archives = build_all(mode="local", output=tmp_path, components=("cdc",))
    assert len(archives) == 2
    wheel = next(path for path in archives if path.suffix == ".whl")
    metadata = check_wheel(wheel, "cdc")
    assert metadata["local_validation_only"] is False
    assert metadata["license_expression"] is None
    assert len(metadata["files"]) == 9
    assert metadata["r_package"]["name"] == "cdcanthro"
    assert metadata["packaging_code_license_expression"] == "MIT"
    assert (tmp_path / "NOT_FOR_PUBLIC_DISTRIBUTION.txt").is_file()
    with zipfile.ZipFile(wheel) as content:
        assert "pedgrowth/data/cdc/data/LOCAL_QA_ONLY.json" not in content.namelist()
        assert not any(
            (name.startswith("pedgrowth/") and not name.startswith("pedgrowth/data/cdc/"))
            or name.startswith("tests/")
            for name in content.namelist()
        )
        assert not any(n.endswith(".lmsb") for n in content.namelist())
        assert not any("/data/source_tables/" in n for n in content.namelist())
        assert "pedgrowth/data/cdc/downloader.py" in content.namelist()
        assert b"License-Expression: MIT" in content.read(
            next(n for n in content.namelist() if n.endswith(".dist-info/METADATA"))
        )
        assert any(n.endswith(".dist-info/entry_points.txt") for n in content.namelist())
        assert any(n.endswith(".dist-info/licenses/SOURCE_RIGHTS.md") for n in content.namelist())
    index = json.loads((tmp_path / "BUILD_MANIFEST.json").read_text())
    assert index["mode"] == "local"
    assert len(index["contents"]) == 2


def test_source_rights_alone_do_not_authorize_publication():
    from pedgrowth.references import _manifest

    current = json.loads((ROOT / "validation" / "source_data" / "SOURCE_LICENSES.json").read_text())
    for family in GROUPS:
        record = current["sources"][family]
        assert record["redistribution_in_mit_core"] is False
        assert record["license_expression"] is None
        assert record["installed_by_default"] is False
        assert record["r_package"]["spdx_license_expression"] in ("GPL-3.0-only", "GPL-3.0-or-later")
        assert record["packaging_code_license_expression"] == (
            "MIT" if family == "cdc" else record["r_package"]["spdx_license_expression"]
        )
        assert record["r_program_license_is_data_redistribution_grant"] is False
        assert all(page["url"].startswith("https://") for page in record["official_reference_pages"])
        assert record["scientific_values_origin"] and record["r_package_usage_and_packaging_basis"]
        assert record["validation"]["input_origin"]
        assert record["validation"]["independent_oracle"]
        assert record["validation"]["generation_scripts"]
    assert len(_manifest()["tables"]) == 33


@pytest.mark.parametrize("family", GROUPS)
def test_publication_builds_only_code_and_provenance(tmp_path: Path, family: str) -> None:
    pytest.importorskip("build")
    pytest.importorskip("setuptools")

    output = tmp_path / family
    artifacts = build_all(mode="publication", output=output, components=(family,))
    assert len(artifacts) == 2
    wheel = next(path for path in artifacts if path.suffix == ".whl")
    sdist = next(path for path in artifacts if path.name.endswith(".tar.gz"))
    details = check_wheel(wheel, family)
    check_sdist(sdist, family, "1.0.0")
    assert details["local_validation_only"] is False
    assert not (output / "NOT_FOR_PUBLIC_DISTRIBUTION.txt").exists()
    assert (output / "BUILD_MANIFEST.json").is_file()


def test_artifact_checks_reject_unexpected_coefficient_csv(tmp_path: Path) -> None:
    pytest.importorskip("build")
    artifacts = build_all(mode="publication", output=tmp_path, components=("cdc",))
    wheel = next(path for path in artifacts if path.suffix == ".whl")
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("pedgrowth/data/cdc/data/extra_scientific_table.csv", "L,M,S\\n1,2,3\\n")
    with pytest.raises(ValueError, match="Reference coefficient values shipped"):
        check_wheel(wheel, "cdc")


def test_sdist_rejects_unexpected_coefficient_resources(tmp_path: Path) -> None:
    pytest.importorskip("build")
    artifacts = build_all(mode="publication", output=tmp_path / "original", components=("cdc",))
    original = next(path for path in artifacts if path.name.endswith(".tar.gz"))
    tampered = tmp_path / "tampered.tar.gz"
    with tarfile.open(original, "r:gz") as source, tarfile.open(tampered, "w:gz") as output:
        for member in source.getmembers():
            content = source.extractfile(member) if member.isfile() else None
            output.addfile(member, content)
        prefix = "pedgrowth_data_cdc-1.0.0/src/pedgrowth/data/cdc/data/"
        payload = b'{"fake_lms": [1, 2, 3]}'
        entry = tarfile.TarInfo(prefix + "hidden_coefficients.json")
        entry.size = len(payload)
        output.addfile(entry, io.BytesIO(payload))
    with pytest.raises(ValueError, match="non-metadata scientific data files"):
        check_sdist(tampered, "cdc", "1.0.0")
