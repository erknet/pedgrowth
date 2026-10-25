"""Reject scientific provider implementations, data, and tests inside the core sdist."""

from __future__ import annotations

import sys
import tarfile
from pathlib import Path


def check_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = {m.name for m in archive.getmembers() if m.isfile()}
        prefix = path.name.removesuffix(".tar.gz") + "/"
        needed = {
            prefix + "pyproject.toml",
            prefix + "src/pedgrowth/__init__.py",
            prefix + "src/pedgrowth/registry.py",
            prefix + "src/pedgrowth/tables/table.py",
        }
        if not needed <= names:
            raise ValueError("Core sdist misses generic reference contracts")
        forbidden = [
            name
            for name in names
            if name.startswith(
                (
                    prefix + "tests/",
                    prefix + "validation/",
                    prefix + "src/pedgrowth/testdata/",
                    prefix + "src/pedgrowth/tables/who/",
                    prefix + "src/pedgrowth/tables/cdc/",
                )
            )
            or (
                name.startswith(prefix + "src/pedgrowth/data/")
                and name != prefix + "src/pedgrowth/data/__init__.py"
            )
            or name.endswith("/tests.py")
            or name.startswith(prefix + "src/pedgrowth/intergrowth")
        ]
        if forbidden:
            raise ValueError(f"Core sdist includes external reference or test assets: {forbidden}")
        print(f"VERIFIED: {path.name}: provider-neutral MIT source distribution")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check_sdist.py <core-sdist>")
    check_sdist(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
