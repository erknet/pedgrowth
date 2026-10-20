"""Monorepo split distribution, optional extras and source licensing boundaries."""

from __future__ import annotations

import json
import tomllib
import zipfile
from pathlib import Path

import pytest

from scripts.build_distributions import GROUPS, _group_table_names, _sources, build_all
from scripts.check_data_distributions import check_wheel

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
        assert (origin / (key + ".csv")).is_file()
        assert len(info["lmsb_sha256"]) == 64
    assert (origin / "intergrowth_coefficients.json").is_file()


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


def test_cdc_build_is_an_independent_local_research_wheel(tmp_path: Path):
    pytest.importorskip("build")
    pytest.importorskip("wheel")
    pytest.importorskip("setuptools")
    archives = build_all(mode="local", output=tmp_path, components=("cdc",))
    assert len(archives) == 2
    wheel = next(path for path in archives if path.suffix == ".whl")
    metadata = check_wheel(wheel, "cdc")
    assert metadata["local_validation_only"] is True
    assert metadata["license_expression"] is None
    assert len(metadata["files"]) == 9
    assert metadata["r_package"]["name"] == "cdcanthro"
    assert metadata["packaging_code_license_expression"] == "MIT"
    assert (tmp_path / "NOT_FOR_PUBLIC_DISTRIBUTION.txt").is_file()
    with zipfile.ZipFile(wheel) as content:
        assert "pedgrowth/data/cdc/data/LOCAL_QA_ONLY.json" in content.namelist()
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
