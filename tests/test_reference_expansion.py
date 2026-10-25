"""WHO/CDC coverage and deterministic binary storage tests."""

import hashlib
import io
import json
from pathlib import Path
from types import MappingProxyType

import pytest
from pedgrowth import GrowthChartsCalculator, Sex
from pedgrowth.compiled import HEADER, decode_binary, encode_csv
from pedgrowth.data.cdc.tables import CDC_TABLES, CdcBmiForAge, CdcBmiForAge2000
from pedgrowth.data.who2006.tables import WHO_ADDITIONAL_TABLES
from pedgrowth.exceptions import DataError, DataNotFoundError
from pedgrowth.reference_data import parse_lms_csv

from tests.reference_sets import WHO_TABLES

DATA = Path(__file__).resolve().parents[1] / "validation" / "source_data"


def test_who_2007_medians_and_age_boundaries():
    calc = GrowthChartsCalculator()
    assert calc.bmifa(15.2641, 61, "M") == pytest.approx(0, abs=1e-12)
    assert calc.lhfa(110.2647, 61, "M") == pytest.approx(0, abs=1e-12)
    assert calc.wfa(18.2579, 61, "F") == pytest.approx(0, abs=1e-12)
    assert calc.bmifa(22.1883, 228, "M") == pytest.approx(0, abs=1e-12)
    assert calc.lhfa(163.1548, 228, "F") == pytest.approx(0, abs=1e-12)
    with pytest.raises(DataNotFoundError):
        calc.wfa(40, 121, "M")
    with pytest.raises(DataNotFoundError):
        calc.bmifa(21, 229, "M")


def test_who_adolescent_precedence_then_cdc_fallback():
    calc = GrowthChartsCalculator(include_cdc=True)
    cdc = GrowthChartsCalculator(override_tables=CDC_TABLES)
    assert calc.bmifa(20, 100, "M") != pytest.approx(cdc.bmifa(20, 100, "M"))
    assert calc.wfa(40, 130, "M") == pytest.approx(cdc.wfa(40, 130, "M"))


def test_who_arm_and_skinfold_measures():
    calc = GrowthChartsCalculator()
    assert len(WHO_ADDITIONAL_TABLES) == 6
    age = 91 / 30.4375
    assert calc.muacfa(13.4779, age, "M") == pytest.approx(0, abs=1e-12)
    assert calc.tsfa(9.7658, age, "M") == pytest.approx(0, abs=1e-12)
    assert calc.ssfa(7.7874, age, "F") == pytest.approx(0, abs=1e-12)
    with pytest.raises(DataNotFoundError):
        calc.tsfa(10, 0, "M")


def test_cdc_2000_vs_extended_bmi():
    original, extended = CdcBmiForAge2000(), CdcBmiForAge()
    for sex in (Sex.Male, Sex.Female):
        median = original.get_lms(50.5, sex).m
        assert original.calculate_zscore(50.5, median, sex) == pytest.approx(0)
        assert original.calculate_zscore(50.5, median, sex) == pytest.approx(
            extended.calculate_zscore(50.5, median, sex)
        )
        assert original.calculate_zscore(50.5, 35, sex) != pytest.approx(
            extended.calculate_zscore(50.5, 35, sex)
        )


def test_registry_has_33_pinned_sources():
    manifest = json.loads((DATA / "SOURCES.json").read_text())
    classes = [*WHO_TABLES, *CDC_TABLES]
    assert len(classes) == len(manifest["tables"]) == 33
    assert {cls().get_file_name() for cls in classes} == set(manifest["tables"])
    for name, info in manifest["tables"].items():
        assert len(info["source_sha256"]) == 64
        assert len(info["csv_sha256"]) == 64
        assert info["reference_version"]
        assert hashlib.sha256((DATA / (name + ".csv")).read_bytes()).hexdigest() == info["csv_sha256"]


@pytest.mark.parametrize("path", sorted(DATA.glob("*.csv")), ids=lambda p: p.stem)
def test_compiler_matches_original_floats(path):
    contents = path.read_bytes()
    packed = encode_csv(contents)
    assert packed == encode_csv(contents)
    decoded = decode_binary(packed, hashlib.sha256(contents).hexdigest())
    assert isinstance(decoded, MappingProxyType)
    parsed = parse_lms_csv(io.StringIO(contents.decode("utf-8-sig")), path.stem)
    assert dict(decoded) == parsed


def test_reject_corrupt_binary():
    packed = encode_csv((DATA / "who2007_weight_for_age_boys.csv").read_bytes())
    with pytest.raises(DataError):
        decode_binary(packed, "a" * 64)
    with pytest.raises(DataError):
        decode_binary(packed[: HEADER.size + 5])
    with pytest.raises(DataError):
        decode_binary(b"not a valid format" + packed)
