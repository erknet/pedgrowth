"""Verify injected release version in source, wheel and sdist metadata."""

from __future__ import annotations

import argparse
import ast
import email
import re
import tarfile
import zipfile
from pathlib import Path

DISTRIBUTION = "pedgrowth"


def source_version() -> str:
    match = re.search(
        r'(?m)^version = "(\d+\.\d+\.\d+)"$', Path("packages/pedgrowth/pyproject.toml").read_text()
    )
    if match is None:
        raise ValueError("Missing project version")
    version = match.group(1)
    tree = ast.parse(Path("packages/pedgrowth/src/pedgrowth/__init__.py").read_text())
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
    ]
    if len(assignments) != 1 or ast.literal_eval(assignments[0].value) != version:
        raise ValueError("Package __version__ does not match pyproject.toml")
    return version


def verify(expected: str, directory: Path) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", expected):
        raise ValueError("Invalid expected release version")
    if source_version() != expected:
        raise ValueError("Source version differs from selected release")
    # A monorepo release directory also contains the independently licensed
    # source-data wheels/sdists. Only the MIT engine's version is verified here.
    wheels = list(directory.glob(f"{DISTRIBUTION}-{expected}-*.whl"))
    sdists = list(directory.glob(f"{DISTRIBUTION}-{expected}.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Expected exactly one MIT core wheel and one MIT core sdist")
    if wheels[0].name != f"{DISTRIBUTION}-{expected}-py3-none-any.whl":
        raise ValueError("Wheel filename does not match release version")
    if sdists[0].name != f"{DISTRIBUTION}-{expected}.tar.gz":
        raise ValueError("Sdist filename does not match release version")
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata_files = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        if len(metadata_files) != 1:
            raise ValueError("Wheel metadata missing or ambiguous")
        metadata = email.message_from_bytes(archive.read(metadata_files[0]))
        if metadata["Name"] != DISTRIBUTION or metadata["Version"] != expected:
            raise ValueError("Wheel metadata mismatch")
        version_file = archive.read("pedgrowth/__init__.py").decode()
        if f'__version__ = "{expected}"' not in version_file:
            raise ValueError("Wheel runtime version mismatch")
    with tarfile.open(sdists[0], "r:gz") as archive:
        metadata_member = archive.getmember(f"{DISTRIBUTION}-{expected}/PKG-INFO")
        stream = archive.extractfile(metadata_member)
        if stream is None:
            raise ValueError("Missing sdist metadata")
        metadata = email.message_from_bytes(stream.read())
        if metadata["Name"] != DISTRIBUTION or metadata["Version"] != expected:
            raise ValueError("Sdist metadata mismatch")
        version_member = archive.getmember(f"{DISTRIBUTION}-{expected}/src/pedgrowth/__init__.py")
        stream = archive.extractfile(version_member)
        if stream is None or f'__version__ = "{expected}"' not in stream.read().decode():
            raise ValueError("Sdist runtime version mismatch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args()
    verify(args.version, args.dist)
    print(f"Verified pedgrowth {args.version}: source, wheel and sdist agree")
