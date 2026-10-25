"""Regression checks preventing source-release archives from leaking references."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from scripts.check_public_source import REQUIRED_FILES, check_archive, sensitive_source


@pytest.mark.parametrize(
    "name",
    [
        "packages/pedgrowth/src/pedgrowth/tables/cache/who_weight_for_age_boys.csv",
        "packages/pedgrowth/src/pedgrowth/tables/cache/cdc_bmi_for_age.csv",
        "tests/legacy/testdata/MySurvey_z_st.csv",
        "tests/fixtures/intergrowth/ig_png_weight_male_zscores.csv",
        "validation/source_data/intergrowth_coefficients.json",
        "packages/pedgrowth-data-cdc/src/pedgrowth/data/cdc/data/source_tables/example.csv",
    ],
)
def test_scientific_data_is_not_public_source(name: str) -> None:
    assert sensitive_source(name)


def test_public_source_validator_rejects_hidden_legacy_coefficients(tmp_path: Path) -> None:
    path = tmp_path / "candidate.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        for name in sorted(REQUIRED_FILES):
            data = b"public source fixture"
            item = tarfile.TarInfo("pedgrowth/" + name)
            item.size = len(data)
            archive.addfile(item, io.BytesIO(data))
        data = b"L,M,S\\n1,2,3\\n"
        item = tarfile.TarInfo("pedgrowth/packages/pedgrowth/src/pedgrowth/tables/cache/who_example.csv")
        item.size = len(data)
        archive.addfile(item, io.BytesIO(data))
    with pytest.raises(ValueError, match="Scientific/private source file"):
        check_archive(path)
