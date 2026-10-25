"""Optional, individually acknowledged WHO, CDC and INTERGROWTH data sources."""

from pathlib import Path

import pytest
from pedgrowth import GrowthChartsCalculator
from pedgrowth.data.intergrowth import IntergrowthCalculator
from pedgrowth.data.intergrowth.data import read_intergrowth_coefficients
from pedgrowth.exceptions import DataError
from pedgrowth.references import (
    install_reference_source,
    installed_references,
)
from pedgrowth.tables.table import _load_coefficients

SOURCE = Path(__file__).resolve().parents[1] / "validation" / "source_data"


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    store = tmp_path / "sources"
    monkeypatch.setenv("PEDGROWTH_REFERENCE_DIR", str(store))
    _load_coefficients.cache_clear()
    yield store
    _load_coefficients.cache_clear()


def test_empty_core_has_no_reference_data(isolated, monkeypatch):
    assert all(not installed for installed in installed_references().values())
    from pedgrowth import references

    def unavailable(*args, **kwargs):
        raise DataError("Reference acquisition unavailable (offline test)")

    monkeypatch.setattr(references, "fetch_verified_source", unavailable)
    from pedgrowth import acquisition
    from pedgrowth.data.intergrowth import downloader as intergrowth_downloader

    for source in (intergrowth_downloader, acquisition):
        monkeypatch.setattr(source, "fetch_verified_source", unavailable)
    calculator = GrowthChartsCalculator()
    with pytest.warns(RuntimeWarning, match="unavailable"):
        with pytest.raises(DataError, match="acquisition unavailable"):
            calculator.wfa(10.0, 12.0, "M")
    with pytest.raises(DataError, match="acquisition unavailable"):
        IntergrowthCalculator("preterm_postnatal")


def test_install_requires_source_terms_acknowledgment(isolated):
    with pytest.raises(ValueError, match="source-specific terms"):
        install_reference_source("cdc", SOURCE, accept_source_terms=False)
    assert not isolated.exists()


@pytest.mark.parametrize(
    ("source", "count"), [("who2006", 18), ("who2007", 6), ("cdc", 9), ("intergrowth", 1)]
)
def test_install_each_provider_separately(isolated, source, count):
    assert install_reference_source(source, SOURCE, accept_source_terms=True) == count
    results = installed_references()
    assert results[source]
    assert all(not present for key, present in results.items() if key != source)
    if source == "cdc":
        assert isinstance(GrowthChartsCalculator(standard="cdc").wfa(10.4, 22.45, "M"), float)
    if source == "intergrowth":
        assert read_intergrowth_coefficients()
        assert isinstance(IntergrowthCalculator("preterm_postnatal").zscore("weight", 2, 35, "F"), float)


def test_both_who_families_enable_complete_who_calculator(isolated):
    install_reference_source("who2006", SOURCE, accept_source_terms=True)
    install_reference_source("who2007", SOURCE, accept_source_terms=True)
    assert isinstance(GrowthChartsCalculator().wfa(10.4, 22.45, "M"), float)
    assert isinstance(GrowthChartsCalculator().wfa(19.0, 61, "M"), float)


def test_corrupt_source_does_not_partially_install(isolated, tmp_path):
    from pedgrowth.references import _source_files

    input_dir = tmp_path / "external"
    input_dir.mkdir()
    for filename in _source_files("cdc"):
        content = (SOURCE / filename).read_bytes()
        (input_dir / filename).write_bytes(
            content + b"corrupt" if filename == "cdc_bmi_for_age.csv" else content
        )
    with pytest.raises(DataError, match="hash differs"):
        install_reference_source("cdc", input_dir, accept_source_terms=True)
    assert not isolated.exists()


def test_installed_model_integrity_is_verified(isolated):
    install_reference_source("intergrowth", SOURCE, accept_source_terms=True)
    (isolated / "intergrowth_coefficients.json").write_bytes(b"{}")
    with pytest.raises(DataError, match="integrity check failed"):
        read_intergrowth_coefficients()
