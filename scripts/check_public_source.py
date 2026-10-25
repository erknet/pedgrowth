"""Fail closed when a proposed public source tree includes scientific datasets.

Use `--git-index` to check files that would enter a new public commit, and
pass a source archive to validate it before attaching it to a release.
Git history must be inspected separately: .gitignore cannot erase past commits.
"""

from __future__ import annotations

import argparse
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

REQUIRED_FILES = {
    "LICENSE",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "PROVENANCE.md",
    "packages/pedgrowth/src/pedgrowth/acquisition.py",
    ".github/workflows/release.yml",
}


def sensitive_source(path: str) -> bool:
    """Conservative denylist: public source does not require scientific fixtures."""
    relative = path.replace("\\", "/").lstrip("./")
    parts = PurePosixPath(relative).parts
    if not parts:
        return False
    if any(part in {".git", ".local", "__pycache__", ".venv", "source_tables"} for part in parts):
        return True
    if path.endswith((".csv", ".lmsb", ".xlsx", ".xls", ".rds", ".RData", ".dta", ".sas7bdat")):
        return True
    if any(part in {"testdata", "cache"} for part in parts) and (
        "tables" in parts or "tests" in parts or "pygrowup_erknet" in parts
    ):
        return True
    if path.endswith(("intergrowth_coefficients.json", "legacy_outputs.json")):
        return True
    if "tests" in parts and "fixtures" in parts:
        return True
    return False


def check_archive(filename: Path) -> None:
    with tarfile.open(filename, "r:gz") as archive:
        members = archive.getmembers()
        filepaths = [PurePosixPath(member.name) for member in members if member.isfile()]
        prefixes = {path.parts[0] for path in filepaths}
        if len(prefixes) != 1:
            raise ValueError("Public source archive must have exactly one root directory")
        (prefix,) = prefixes
        content = set()
        for member in members:
            name = PurePosixPath(member.name)
            if member.issym() or member.islnk() or ".." in name.parts or name.is_absolute():
                raise ValueError(f"Unsafe source archive member: {member.name}")
            if member.isfile():
                relative = name.relative_to(prefix).as_posix()
                if sensitive_source(relative):
                    raise ValueError(f"Scientific/private source file in public archive: {relative}")
                content.add(relative)
        missing = REQUIRED_FILES - content
        if missing:
            raise ValueError(f"Public archive is missing required files: {sorted(missing)}")


def check_git_index() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "-z"],  # noqa: S607 - git is the required local VCS
        capture_output=True,
        check=True,
    )
    protected = [
        name.decode("utf-8", errors="replace")
        for name in result.stdout.split(b"\x00")
        if name and sensitive_source(name.decode("utf-8", errors="replace"))
    ]
    if protected:
        raise ValueError(f"Private or scientific data are tracked: {protected}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, nargs="?")
    parser.add_argument("--git-index", action="store_true")
    args = parser.parse_args()
    if not args.git_index and args.archive is None:
        parser.error("Supply a source archive or --git-index")
    if args.git_index:
        check_git_index()
        print("Public Git index excludes protected scientific files")
    if args.archive is not None:
        check_archive(args.archive)
        print(f"Verified code-only public source archive: {args.archive.name}")


if __name__ == "__main__":
    main()
