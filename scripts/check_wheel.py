"""Check the MIT-only pedgrowth engine wheel has no provider code or fixtures."""

from __future__ import annotations

import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path


def check_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as wheel:
        names = set(wheel.namelist())
        required = {
            "pedgrowth/__init__.py",
            "pedgrowth/registry.py",
            "pedgrowth/references.py",
            "pedgrowth/tables/table.py",
        }
        if not required <= names:
            raise ValueError("Generic engine is missing its public API or reference contracts")
        forbidden = [
            n
            for n in names
            if n.startswith(
                (
                    "pedgrowth/testdata/",
                    "pedgrowth/tests",
                    "pedgrowth/tables/who/",
                    "pedgrowth/tables/cdc/",
                    "pedgrowth_data_",
                    "tests/",
                    "validation/",
                )
            )
            or (n.startswith("pedgrowth/data/") and n != "pedgrowth/data/__init__.py")
            or "intergrowth" in n.lower()
            and not n.endswith("THIRD_PARTY_NOTICES.md")
        ]
        if forbidden:
            raise ValueError(f"Core wheel improperly contains provider or test assets: {forbidden}")
        metas = [p for p in names if p.endswith(".dist-info/METADATA")]
        if len(metas) != 1:
            raise ValueError("Missing core metadata")
        meta = BytesParser().parsebytes(wheel.read(metas[0]))
        if meta["Name"] != "pedgrowth" or meta["License-Expression"] != "MIT":
            raise ValueError("Generic core license or identity changed")
        requires_dist = meta.get_all("Requires-Dist") or []
        if any("pedgrowth-data" in item for item in requires_dist if "extra ==" not in item):
            raise ValueError("Core must not require a scientific reference extension")
        print(f"VERIFIED: {path.name}: provider-neutral MIT engine, no tests or source coefficients")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check_wheel.py <core-wheel>")
    check_wheel(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
