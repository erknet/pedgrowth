"""Choose a release version using previous release's saved public API schema."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.api_schema import classify, manifest


def next_version(previous_version: str | None, previous_schema: Path | None) -> tuple[str, str]:
    if previous_version is None:
        if previous_schema is not None:
            raise ValueError("Unexpected baseline schema for initial release")
        return "1.0.0", "initial"
    if previous_schema is None or not previous_schema.is_file():
        raise ValueError("Missing published API schema: refusing to guess version")
    if not re.fullmatch(r"\d+\.\d+\.\d+", previous_version):
        raise ValueError("Invalid previous release version")
    change, _ = classify(json.loads(previous_schema.read_text()), manifest())
    major, minor, patch = map(int, previous_version.split("."))
    if change == "major":
        return f"{major + 1}.0.0", change
    if change == "minor":
        return f"{major}.{minor + 1}.0", change
    return f"{major}.{minor}.{patch + 1}", change


def set_version(version: str) -> None:
    roots = sorted(Path("packages").glob("*/pyproject.toml"))
    locations = [(str(filename), r'(?m)^version = "[^"]+"') for filename in roots] + [
        ("packages/pedgrowth/src/pedgrowth/__init__.py", r'(?m)^__version__ = "[^"]+"')
    ]
    for filename, pattern in locations:
        path = Path(filename)
        updated, count = re.subn(
            pattern, lambda m: m.group().split("=")[0] + f'= "{version}"', path.read_text()
        )
        if count != 1:
            raise RuntimeError(f"Invalid version declaration: {filename}")
        updated = re.sub(
            r"(pedgrowth(?:-data-(?:who2006|who2007|cdc|intergrowth))?==)\d+\.\d+\.\d+",
            lambda m: m.group(1) + version,
            updated,
        )
        path.write_text(updated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-version")
    parser.add_argument("--previous-schema", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    version, change = next_version(args.previous_version, args.previous_schema)
    if args.write:
        set_version(version)
    print(version)
