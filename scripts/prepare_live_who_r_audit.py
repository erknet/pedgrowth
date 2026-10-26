"""Regenerate private-free WHO R comparison inputs from pinned official sources.

For GitHub's public code-only checkout: reference CSVs are downloaded, checked,
and written to a transient CI directory. Do not commit or upload that directory.
The independent R audit reads these files and compares LMS coefficients with
the original WHO-authored anthro and anthroplus packages.
"""

from __future__ import annotations

import argparse
import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from pedgrowth.acquisition import normalize_spreadsheet
from pedgrowth.compiled import encode_csv
from pedgrowth.data.who2006.downloader import TABLE_CLASSES as WHO2006_TABLES
from pedgrowth.data.who2007.downloader import TABLE_CLASSES as WHO2007_TABLES
from pedgrowth.references import fetch_verified_source
from pedgrowth.registry import registry
from pedgrowth.tables.table import GrowthTable

PROVIDERS: dict[str, Mapping[str, type[GrowthTable]]] = {
    "who2006": WHO2006_TABLES,
    "who2007": WHO2007_TABLES,
}


def prepare(output_dir: Path) -> list[Path]:
    """Export *only* audited WHO coefficients; fail on any source drift."""
    output_dir = output_dir.resolve()
    # Public CI should never write generated scientific data into the Git tree
    # or a distributable Python package directory.
    root = Path(__file__).resolve().parents[1]
    allowed = (root / ".local").resolve()
    if not output_dir.is_relative_to(allowed) or output_dir == allowed:
        raise ValueError("Live scientific coefficient output must be under .local/")
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for provider_name, table_classes in PROVIDERS.items():
        manifest = cast(dict[str, dict[str, Any]], registry.provider(provider_name).manifest()["tables"])
        if set(manifest) != set(table_classes):
            raise RuntimeError(f"{provider_name}: original-source table coverage drift")
        if len(manifest) != (18 if provider_name == "who2006" else 6):
            raise RuntimeError(f"{provider_name}: unexpected original-source table count")
        for name, entry in sorted(manifest.items()):
            target = output_dir / (name + ".csv")
            if target.exists():
                raise RuntimeError(f"Refusing to overwrite prior source audit file: {target.name}")
            source = fetch_verified_source(str(entry["source_url"]), str(entry["source_sha256"]))
            table_type = cast(Any, table_classes[name])
            normalized = normalize_spreadsheet(source, table_type)
            if hashlib.sha256(normalized).hexdigest() != entry["csv_sha256"]:
                raise RuntimeError(f"{name}: normalized scientific source digest mismatch")
            compiled = encode_csv(normalized)
            if hashlib.sha256(compiled).hexdigest() != entry["lmsb_sha256"]:
                raise RuntimeError(f"{name}: compiled scientific source digest mismatch")
            target.write_bytes(normalized)
            written.append(target)
            print(f"Verified live source and normalized coefficients: {name}", flush=True)
    if len(written) != 24:
        raise RuntimeError(f"Expected 24 WHO 2006/2007 tables, got {len(written)}")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    files = prepare(args.output_dir)
    print(f"Prepared {len(files)}/24 verified temporary WHO tables; never upload these inputs")


if __name__ == "__main__":
    main()
