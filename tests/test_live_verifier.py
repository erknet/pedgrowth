"""Non-network tests of the live source-hash and content validator."""

import hashlib
import json
from pathlib import Path

from scripts import refresh_data

DATA = Path(__file__).resolve().parents[1] / "validation" / "source_data"
NAME = "who2007_weight_for_age_boys"


def _snapshot():
    manifest = json.loads((DATA / "SOURCES.json").read_text())
    return {"tables": {NAME: dict(manifest["tables"][NAME])}}


def test_live_requires_both_source_hash_and_content_to_match(monkeypatch, capsys):
    good_content = (DATA / (NAME + ".csv")).read_bytes()
    monkeypatch.setattr(refresh_data, "fetch", lambda _: b"example upstream data")
    monkeypatch.setattr(refresh_data, "normalized_source", lambda *_: good_content)
    manifest = _snapshot()
    manifest["tables"][NAME]["source_sha256"] = hashlib.sha256(b"example upstream data").hexdigest()
    assert refresh_data.live(manifest, only={NAME}, workers=1) == 0
    assert "normalized_content=IDENTICAL" in capsys.readouterr().out

    manifest["tables"][NAME]["source_sha256"] = "0" * 64
    assert refresh_data.live(manifest, only={NAME}, workers=1) == 1
    assert "source_sha256=DIFF" in capsys.readouterr().out

    monkeypatch.setattr(refresh_data, "normalized_source", lambda *_: b"modified table")
    manifest["tables"][NAME]["source_sha256"] = hashlib.sha256(b"example upstream data").hexdigest()
    assert refresh_data.live(manifest, only={NAME}, workers=1) == 1
    assert "normalized_content=DIFFERENT" in capsys.readouterr().out


def test_live_fails_closed_when_official_site_unreachable(monkeypatch, capsys):
    def offline(_):
        raise ConnectionError("site unavailable")

    monkeypatch.setattr(refresh_data, "fetch", offline)
    assert refresh_data.live(_snapshot(), only={NAME}, workers=1) == 1
    assert "site unavailable" in capsys.readouterr().out
