"""Verified CDC source acquisition, retry, and scientific-preservation tests."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

import pytest
from pedgrowth import acquisition
from pedgrowth.compiled import encode_csv
from pedgrowth.data.cdc import downloader as cdc
from pedgrowth.exceptions import DataError
from pedgrowth.registry import registry


def test_official_download_uses_identified_browser_compatible_user_agent(monkeypatch):
    import urllib.request

    from pedgrowth.references import fetch_verified_source

    source = b"Sex,Agemos,L,M,S\r\n1,0,1.0,3.0,0.1\r\n"
    captured: list[str] = []

    class Response:
        headers = {"Content-Length": str(len(source))}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def geturl(self):
            return "https://www.cdc.gov/growthcharts/data/example.csv"

        def read(self, length):
            return source

    def fake_open(request, timeout):
        captured.append(request.get_header("User-agent"))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    assert (
        fetch_verified_source(
            "https://www.cdc.gov/growthcharts/data/example.csv",
            hashlib.sha256(source).hexdigest(),
        )
        == source
    )
    assert len(captured) == 1
    assert captured[0].startswith("Mozilla/5.0")
    assert "pedgrowth" in captured[0] and "erknet/pedgrowth" in captured[0]


SOURCES = Path(__file__).resolve().parents[1] / "validation/source_data"
METADATA = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "packages/pedgrowth-data-cdc/src/pedgrowth/data/cdc/data/SOURCES.json"
    ).read_text()
)["tables"]


def _source_from_normalized(name: str) -> bytes:
    """Make the CDC-shaped source CSV from scientific fixture coordinates."""
    normalized = list(csv.reader(io.StringIO((SOURCES / (name + ".csv")).read_text())))
    extended_bmi = name == "cdc_bmi_for_age"
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Sex", "Agemos", "L", "M", "S", *("Col" + str(i) for i in range(5, 15))])
    for row in normalized[1:]:
        official = [""] * 15
        official[0] = "1" if row[0] == "M" else "2"
        official[1:5] = row[1:5]
        if extended_bmi:
            official[5] = row[5]
            official[14] = row[6]
        writer.writerow(official)
    return output.getvalue().encode("utf-8")


@pytest.mark.parametrize("name", tuple(METADATA))
def test_cdc_normalization_preserves_all_scientific_values(name: str) -> None:
    source = _source_from_normalized(name)
    normalized = cdc.normalize_source(source, cdc.TABLE_CLASSES[name])
    assert hashlib.sha256(normalized).hexdigest() == METADATA[name]["csv_sha256"]
    assert hashlib.sha256(encode_csv(normalized)).hexdigest() == METADATA[name]["lmsb_sha256"]


def test_missing_cdc_source_does_not_block_other_table_and_is_retried(tmp_path, monkeypatch):
    first, second = tuple(sorted(METADATA))[:2]
    sources = {name: _source_from_normalized(name) for name in (first, second)}
    checksums = {
        name: {
            **METADATA[name],
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "source_url": f"https://www.cdc.gov/test/{name}.csv",
        }
        for name, source in sources.items()
    }

    class TestProvider:
        name = "cdc"

        def manifest(self):
            return {"tables": checksums}

    original_provider = registry.provider
    monkeypatch.setattr(
        registry,
        "provider",
        lambda family: TestProvider() if family == "cdc" else original_provider(family),
    )
    monkeypatch.setattr(acquisition, "provider_cache", lambda _: tmp_path)
    monkeypatch.setattr(
        acquisition,
        "read_resource",
        lambda filename: (tmp_path / filename).read_bytes() if (tmp_path / filename).is_file() else None,
    )
    missing_attempts = 0

    def fetch(url, sha256):
        nonlocal missing_attempts
        name = url.split("/")[-1].removesuffix(".csv")
        data = sources[name]
        assert hashlib.sha256(data).hexdigest() == sha256
        if name == first and missing_attempts == 0:
            missing_attempts += 1
            raise DataError("CDC temporarily unavailable (HTTP 403)")
        return data

    monkeypatch.setattr(acquisition, "fetch_verified_source", fetch)
    with pytest.warns(RuntimeWarning, match="HTTP 403"):
        assert cdc.initialize_data() == 1
    assert (tmp_path / (second + ".lmsb")).exists()
    assert not (tmp_path / (first + ".lmsb")).exists()
    assert cdc.initialize_data(first + ".lmsb") == 1
    assert cdc.initialize_data() == 0
    assert missing_attempts == 1
    assert all((tmp_path / (name + ".lmsb")).exists() for name in sources)
