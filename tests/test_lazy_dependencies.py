"""Private-cache lazy acquisition and bulk provider initialization regression tests."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from pedgrowth import acquisition
from pedgrowth.compiled import decode_binary, encode_csv
from pedgrowth.data import download_missing_dependencies
from pedgrowth.data.intergrowth import downloader as intergrowth
from pedgrowth.data.who2006 import downloader as who2006
from pedgrowth.exceptions import DataError
from pedgrowth.registry import ReferenceProvider, registry


def test_optional_bulk_initialization_visits_registered_extensions(monkeypatch):
    calls: list[str] = []
    providers = (
        ReferenceProvider("first", "test", "test", initialize_data=lambda: calls.append("first") or 3),
        ReferenceProvider("second", "test", "test", initialize_data=lambda: calls.append("second") or 0),
        ReferenceProvider("bundled", "test", "test"),
    )
    monkeypatch.setattr(registry, "providers", lambda: providers)
    assert download_missing_dependencies() == {"first": 3, "second": 0, "bundled": 0}
    assert calls == ["first", "second"]


def test_intergrowth_parameters_can_be_reconstructed_without_shipping_them():
    """Simulate the audited upstream R functions using reference fixture numbers."""
    source = Path(__file__).resolve().parents[1] / "validation/source_data/intergrowth_coefficients.json"
    parameters = json.loads(source.read_text())
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, function, keys in (
            ("ig_png.R", "ig_png_mu_sigma", intergrowth._POSTNATAL_NAMES),
            ("ig_vpns.R", "ig_vpns_mu_sigma", intergrowth._BIRTH_NAMES),
        ):
            body = (
                function
                + " <- function(x) {\n  "
                + " + ".join(repr(parameters[key]) for key in keys)
                + "\n}\n"
            )
            content = body.encode()
            entry = tarfile.TarInfo("gigs/R/" + name)
            entry.size = len(content)
            archive.addfile(entry, io.BytesIO(content))
    derived = intergrowth.reconstruct_coefficients(output.getvalue())
    assert json.loads(derived) == parameters
    assert (
        hashlib.sha256(derived).hexdigest()
        == "fe3d62fd373d567ffe8be804c4fc80a0dad667084d831afc899ba9441b61bb13"
    )


def test_who_spreadsheet_conversion_and_binary_packaging():
    from openpyxl import Workbook

    name, cls = next(iter(who2006.TABLE_CLASSES.items()))
    table = cls.__new__(cls)
    book = Workbook()
    sheet = book.active
    sheet.append(["Day", "L", "M", "S"])
    for i in range(32):
        sheet.append([i, 1.0, 4.0 + i / 10, 0.1])
    buffer = io.BytesIO()
    book.save(buffer)
    content = who2006._normalize(buffer.getvalue(), cls)
    binary = encode_csv(content)
    result = decode_binary(binary, hashlib.sha256(content).hexdigest())
    assert len(next(iter(result.values()))) == 32
    assert name.startswith("who_")
    assert table.get_file_name() == name


def test_provider_download_uses_verified_cache_without_network(tmp_path, monkeypatch):
    from pedgrowth.data.who2006.downloader import initialize_data

    name, cls = next(iter(who2006.TABLE_CLASSES.items()))
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.append(["Day", "L", "M", "S"])
    for i in range(32):
        sheet.append([i, 1.0, 4.0 + i / 10, 0.1])
    buffer = io.BytesIO()
    book.save(buffer)
    source = buffer.getvalue()
    csv = who2006._normalize(source, cls)
    packed = encode_csv(csv)
    info = {
        "source_url": "https://www.who.int/verified-test.xlsx",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "csv_sha256": hashlib.sha256(csv).hexdigest(),
        "lmsb_sha256": hashlib.sha256(packed).hexdigest(),
    }

    class FixtureProvider:
        name = "who2006"

        def manifest(self):
            return {"tables": {name: info}}

    original_provider = registry.provider
    monkeypatch.setattr(
        registry,
        "provider",
        lambda family: FixtureProvider() if family == "who2006" else original_provider(family),
    )
    monkeypatch.setattr(acquisition, "provider_cache", lambda provider: tmp_path)
    monkeypatch.setattr(
        acquisition,
        "read_resource",
        lambda filename: (tmp_path / filename).read_bytes() if (tmp_path / filename).is_file() else None,
    )
    downloads: list[str] = []

    def fake_fetch(url, sha256):
        downloads.append(url)
        assert url == info["source_url"]
        assert sha256 == info["source_sha256"]
        if len(downloads) == 1:
            raise DataError("transient source outage")
        return source

    monkeypatch.setattr(acquisition, "fetch_verified_source", fake_fetch)
    with pytest.raises(DataError, match="transient source outage"):
        initialize_data(name + ".lmsb")
    assert not (tmp_path / (name + ".lmsb")).exists()
    assert initialize_data(name + ".lmsb") == 1
    assert (tmp_path / (name + ".lmsb")).read_bytes() == packed
    assert initialize_data() == 0
    assert downloads == [info["source_url"], info["source_url"]]


def test_bulk_initializer_reports_failures_and_retries(monkeypatch):
    attempts = 0

    def initially_unavailable() -> int:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise DataError("upstream source temporarily unavailable")
        return 1

    provider = ReferenceProvider("retry", "synthetic", "test", initialize_data=initially_unavailable)
    monkeypatch.setattr(registry, "providers", lambda: (provider,))
    with pytest.warns(RuntimeWarning, match="retry"):
        assert download_missing_dependencies() == {"retry": 0}
    assert download_missing_dependencies() == {"retry": 1}
    assert attempts == 2


def test_plan_construction_does_not_fetch_irrelevant_data(tmp_path, monkeypatch):
    from pedgrowth import GrowthChartsCalculator
    from pedgrowth.data.who2006 import WhoPlan

    monkeypatch.setenv("PEDGROWTH_REFERENCE_DIR", str(tmp_path))

    def no_unexpected_download(*args, **kwargs):
        raise AssertionError("No downloads permitted before a table is requested")

    monkeypatch.setattr(acquisition, "fetch_verified_source", no_unexpected_download)
    plan = WhoPlan()
    calculator = GrowthChartsCalculator(plan=plan)
    assert calculator.plan is plan
    assert "who_weight_for_age_boys" in calculator.available_references()
    assert GrowthChartsCalculator() is not None


def test_ignored_scientific_source_files():
    rules = (Path(__file__).resolve().parents[1] / ".gitignore").read_text()
    assert "who2006/data/*.lmsb" in rules
    assert "who2007/data/*.lmsb" in rules
    assert "intergrowth_coefficients.json" in rules
    assert "validation/source_data/*.csv" in rules
