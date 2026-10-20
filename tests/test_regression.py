"""Numerical regression against the original 0.9.4 implementation.

All 448 legacy samples are retained. The corrected BMI threshold is tested
separately using a point between the 95th and 97.5th percentiles.
"""

import json
import math
from pathlib import Path
from statistics import NormalDist

import pytest
from pedgrowth import GrowthChartsCalculator, Sex, TableType, exceptions
from pedgrowth.data.cdc.tables import CDC_TABLES, CdcBmiForAge, CdcWeightForAgeInfant
from pedgrowth.tables.math import calculate_value_by_percentile, percentile_to_z, z_to_percentile

from tests.reference_sets import WHO_TABLES

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "legacy_outputs.json").read_text())


def published_p95_changes_result(sample: dict[str, object]) -> bool:
    if sample["table"] != "CdcBmiForAge":
        return False
    row = CdcBmiForAge().get_lms(float(sample["index"]), Sex(str(sample["sex"])))
    return row.p95 is not None and float(sample["measurement"]) > row.p95


WHO_TAIL_CORRECTED = {
    "WhoWeightForAgeBoys",
    "WhoWeightForAgeGirls",
    "WhoMuacBoys",
    "WhoMuacGirls",
    "WhoTricepsBoys",
    "WhoTricepsGirls",
    "WhoSubscapularBoys",
    "WhoSubscapularGirls",
}


def who_tail_corrected(sample: dict[str, object]) -> bool:
    return str(sample["table"]) in WHO_TAIL_CORRECTED and abs(float(sample["expected"])) > 3


TABLES = {cls.__name__: cls for cls in [*WHO_TABLES, *CDC_TABLES]}


@pytest.mark.parametrize(
    "sample",
    [row for row in FIXTURES if not published_p95_changes_result(row) and not who_tail_corrected(row)],
)
def test_unchanged_legacy_lms_results(sample):
    table = TABLES[sample["table"]]()
    sex = Sex(sample["sex"]) if sample["sex"] else None
    actual = table.calculate_zscore(sample["index"], sample["measurement"], sex)
    assert actual == pytest.approx(sample["expected"], abs=1e-11)


@pytest.mark.parametrize("sample", [row for row in FIXTURES if who_tail_corrected(row)])
def test_legacy_who_tail_is_intentionally_corrected(sample):
    # Keep the historical fixture untouched: the published WHO R oracle is
    # authoritative beyond +/-3 SD, not the old uncorrected LMS output.
    table = TABLES[sample["table"]]()
    actual = table.calculate_zscore(
        sample["index"], sample["measurement"], Sex(sample["sex"]) if sample["sex"] else None
    )
    assert abs(actual - float(sample["expected"])) > 1e-5


@pytest.mark.parametrize("sample", [row for row in FIXTURES if published_p95_changes_result(row)])
def test_corrected_legacy_bmi_samples(sample):
    table = CdcBmiForAge()
    sex = Sex(sample["sex"])
    lms = table.get_lms(sample["index"], sex)
    p95 = lms.p95
    assert p95 is not None
    expected = NormalDist().inv_cdf(0.90 + 0.10 * NormalDist().cdf((sample["measurement"] - p95) / lms.sigma))
    assert table.calculate_zscore(sample["index"], sample["measurement"], sex) == pytest.approx(expected)
    assert abs(expected - sample["expected"]) > 1e-9


def test_cdc_extended_bmi_threshold_is_95th_percentile():
    """2022 CDC extended BMI applies strictly above BMI95, not BMI97.5."""
    table = CdcBmiForAge()
    index, sex = 50.5, Sex.Male
    lms = table.get_lms(index, sex)
    p95 = lms.p95
    assert p95 is not None
    assert p95 == pytest.approx(17.8219)
    assert table.calculate_zscore(index, p95, sex) == pytest.approx(NormalDist().inv_cdf(0.95), abs=0.001)
    above = p95 + 0.1
    actual = table.calculate_zscore(index, above, sex)
    expected = NormalDist().inv_cdf(0.90 + 0.10 * NormalDist().cdf((above - p95) / lms.sigma))
    assert actual == pytest.approx(expected, abs=1e-12)

    # Original implementation used the ordinary LMS value in this interval.
    legacy_lms = ((above / lms.m) ** lms.l - 1) / (lms.l * lms.s)
    assert abs(actual - legacy_lms) > 1e-6


def test_cdc_published_weight_for_age_example():
    # CDC documentation: male, 9 months, 9.7 kg -> z about +0.207.
    table = CdcWeightForAgeInfant()
    lms = table.get_lms(9.5, Sex.Male)
    assert lms.m == pytest.approx(9.476500305)
    assert table.calculate_zscore(9.5, 9.7, Sex.Male) == pytest.approx(0.207, abs=0.002)


def test_math_percentiles_are_conventional_cumulative_proportions():
    assert z_to_percentile(0) == pytest.approx(0.5)
    assert percentile_to_z(0.95) == pytest.approx(1.6448536269514722)
    assert calculate_value_by_percentile(0.5, CdcBmiForAge().get_lms(50.5, Sex.Male)) > 0


def test_default_who_and_explicit_cdc_selection():
    who = GrowthChartsCalculator()
    cdc = GrowthChartsCalculator(override_tables=CDC_TABLES)
    combined = GrowthChartsCalculator(include_cdc=True)
    assert who.wfa(10.4, 22.45, "M") == pytest.approx(combined.wfa(10.4, 22.45, "M"))
    assert cdc.wfa(10.4, 22.45, "M") != pytest.approx(who.wfa(10.4, 22.45, "M"))
    assert combined.wfa(46, 120, "F") != pytest.approx(cdc.wfa(46, 120, "F"))
    assert combined.wfa(46, 130, "F") == pytest.approx(cdc.wfa(46, 130, "F"))


def test_height_alias_and_legacy_typo():
    assert TableType.WeightForHeigt is TableType.WeightForHeight
    calc = GrowthChartsCalculator()
    assert calc.wfh(15, "M", 90) == pytest.approx(calc.zscore_for_measurement("wfh", 15, "M", 90))
    assert calc.wfl(15, "M", 90) == pytest.approx(calc.zscore_for_measurement("wfl", 15, "M", 90))


def test_missing_measurement_is_preserved():
    assert GrowthChartsCalculator().wfa(None, age_in_months=12, sex="M") is None


@pytest.mark.parametrize(
    ("value", "exception"),
    [
        ("nan", exceptions.InvalidMeasurement),
        (float("inf"), exceptions.InvalidMeasurement),
        (-2, exceptions.InvalidMeasurement),
        (0, exceptions.InvalidMeasurement),
        (True, exceptions.InvalidMeasurement),
    ],
)
def test_invalid_measurements(value, exception):
    with pytest.raises(exception):
        GrowthChartsCalculator().wfa(value, 12, "M")


@pytest.mark.parametrize("age", [-1, "nan", None, float("inf"), "abc", True])
def test_invalid_ages(age):
    with pytest.raises(exceptions.InvalidAgeError):
        GrowthChartsCalculator().wfa(10, age, "M")


@pytest.mark.parametrize("value", [0, -1, "nan", "", None, True])
def test_invalid_lengths(value):
    with pytest.raises(exceptions.InvalidLengthError):
        GrowthChartsCalculator().wfl(10, "M", value)


@pytest.mark.parametrize("sex", ["X", "", None, 5])
def test_invalid_sex(sex):
    with pytest.raises(exceptions.InvalidSexError):
        GrowthChartsCalculator().wfa(10, 12, sex)


def test_out_of_range_and_bad_indicator():
    with pytest.raises(exceptions.DataNotFoundError):
        GrowthChartsCalculator().wfa(10, 1000, "M")
    with pytest.raises(exceptions.InvalidTableNameError):
        GrowthChartsCalculator().zscore_for_measurement("banana", 10, "M", 12)


def test_package_loads_offline(monkeypatch):
    import socket

    def block_network(*args, **kwargs):
        raise AssertionError("Unexpected network access during GrowthChartsCalculator()")

    monkeypatch.setattr(socket.socket, "connect", block_network)
    calc = GrowthChartsCalculator(include_cdc=True)
    assert math.isfinite(calc.wfa(10.4, 22.45, "M"))


def test_no_missing_packaged_coefficients():
    import hashlib
    from importlib.resources import files

    from pedgrowth.registry import registry

    assert not any(files("pedgrowth").joinpath("data").glob("*.lmsb"))
    assert sum(len(provider.manifest().get("tables", {})) for provider in registry.providers()) == 33
    for provider in registry.providers():
        for name, record in provider.manifest().get("tables", {}).items():
            csv_content = files(provider.module).joinpath("data", "source_tables", name + ".csv").read_bytes()
            assert hashlib.sha256(csv_content).hexdigest() == record["csv_sha256"]


def test_missing_data_has_clear_error():
    from pedgrowth.tables.table import _load_coefficients

    with pytest.raises(exceptions.DataError):
        _load_coefficients("not-a-real-dataset")


def test_recumbent_height_adjustment_changes_result():
    calc = GrowthChartsCalculator(adjust_height_data=True)
    assert calc.lhfa(88, 18, "M", True) != calc.lhfa(88, 18, "M", False)
