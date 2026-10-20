"""Fetch immutable official CDC percentile observations for independent validation.

The source P3/P5/P50/P95 columns are published observations, not values
computed from the package's bundled LMS coefficients. Never silently regenerate
these snapshots during pytest.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen  # noqa: S310

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "tests/fixtures/official_percentiles"
MANIFEST = json.loads((ROOT / "validation/source_data/SOURCES.json").read_text())["tables"]


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    catalog = {}
    for name, meta in sorted(MANIFEST.items()):
        if meta["standard"] != "CDC":
            continue
        url = meta["source_url"]
        if not url.startswith("https://www.cdc.gov/"):
            raise ValueError(f"Unexpected source host: {url}")
        raw = urlopen(url, timeout=30).read()  # noqa: S310
        digest = hashlib.sha256(raw).hexdigest()
        if digest != meta["source_sha256"]:
            raise RuntimeError(f"{name}: official source hash changed: {digest}")
        source = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        records = []
        for row in source:
            normalized = {k.lower(): v for k, v in row.items() if k}
            age = normalized.get("agemos")
            if age is None:
                age = normalized.get("length") or normalized.get("stature") or normalized.get("height")
            if age is None:
                raise RuntimeError(f"{name}: unknown official index columns {list(normalized)}")
            if age.lower() in ("agemos", "length", "stature", "height"):
                continue
            sex = normalized.get("sex")
            if sex is None:
                raise RuntimeError(f"{name}: no sex")
            for percentile in ("p3", "p5", "p50", "p95"):
                value = normalized.get(percentile)
                if value and value.strip():
                    records.append((sex, age, percentile, value))
        if not records:
            raise RuntimeError(f"{name}: no published percentile observations")
        output = DEST / f"{name}.csv"
        with output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(("sex", "coordinate", "percentile", "measurement"))
            writer.writerows(records)
        catalog[name] = {
            "url": url,
            "source_sha256": digest,
            "fixture_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "observations": len(records),
        }
    (DEST / "manifest.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(
        f"Fetched {len(catalog)} CDC official source datasets, {sum(x['observations'] for x in catalog.values())} published percentile observations"
    )


if __name__ == "__main__":
    main()
