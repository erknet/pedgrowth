"""Load independently registered reference resources with source-hash verification.

The generic engine has no knowledge of specific providers or scientific models.
Optional extensions declare resources, tables, plans and checksums.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import time
import urllib.request
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Any, cast

from .exceptions import DataError
from .registry import ReferenceProvider, registry


def _providers() -> tuple[ReferenceProvider, ...]:
    return registry.providers()


def _catalog() -> dict[str, tuple[ReferenceProvider, dict[str, Any]]]:
    result: dict[str, tuple[ReferenceProvider, dict[str, Any]]] = {}
    for provider in _providers():
        manifest = provider.manifest()
        if "tables" in manifest:
            for name, info in manifest["tables"].items():
                if name in result:
                    raise DataError(f"Duplicate provider resource: {name}")
                result[name] = (provider, info)
        for filename, digest in (provider.additional_resources or {}).items():
            stem = filename.removesuffix(".json")
            if stem in result:
                raise DataError(f"Duplicate extension resource {filename!r}")
            result[stem] = (provider, {"csv_sha256": digest, "original_filename": filename})
    return result


def reference_directory() -> Path:
    user_choice = os.environ.get("PEDGROWTH_REFERENCE_DIR")
    if user_choice:
        return Path(user_choice).expanduser()
    if os.name == "nt":
        data_home = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(data_home) / "pedgrowth" / "references"
    xdg = os.environ.get("XDG_DATA_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "share") / "pedgrowth" / "references"


def _expected_digest(name: str) -> str:
    stem = name.removesuffix(".csv").removesuffix(".lmsb").removesuffix(".json")
    entries = _catalog()
    if stem not in entries:
        raise DataError(f"Unknown or unavailable growth reference: {stem!r}")
    _, meta = entries[stem]
    if name.endswith(".lmsb"):
        return str(meta["lmsb_sha256"])
    return str(meta["csv_sha256"])


def provider_cache(provider: ReferenceProvider) -> Path:
    """Version the provider cache by its exact audited source manifest."""
    root = reference_directory()
    if "PEDGROWTH_REFERENCE_DIR" in os.environ:
        return root
    import json

    manifest = json.dumps(provider.manifest(), sort_keys=True, separators=(",", ":")).encode()
    return root / provider.name / hashlib.sha256(manifest).hexdigest()[:16]


def _candidate_files(filename: str) -> tuple[Any, ...]:
    directory = reference_directory()
    stem = filename.removesuffix(".csv").removesuffix(".lmsb").removesuffix(".json")
    provider, _ = _catalog()[stem]
    target = provider_cache(provider) / filename
    if "PEDGROWTH_REFERENCE_DIR" in os.environ:
        return (target,)
    return (target, directory / filename, resources.files(provider.module).joinpath("data", filename))


def read_resource(filename: str) -> bytes | None:
    if not filename or "/" in filename or "\\" in filename or filename.startswith("."):
        raise DataError(f"Invalid reference resource name: {filename!r}")
    expected = _expected_digest(filename)
    for path in _candidate_files(filename):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise DataError(f"Reference resource integrity check failed: {filename}")
        if filename.endswith(".lmsb"):
            from .compiled import decode_binary

            base = filename.removesuffix(".lmsb")
            source_checksum = _catalog()[base][1]["csv_sha256"]
            decode_binary(data, source_checksum)
        return cast(bytes, data)
    return None


def ensure_resource(filename: str) -> bytes:
    """Lazy verified reference acquisition, never during package registration."""
    try:
        content = read_resource(filename)
    except DataError:
        if "PEDGROWTH_REFERENCE_DIR" in os.environ:
            raise  # Never overwrite unverified user-supplied resources.
        content = None
    if content is not None:
        return content
    stem = filename.removesuffix(".csv").removesuffix(".lmsb").removesuffix(".json")
    entry = _catalog().get(stem)
    if entry is None:
        raise DataError(f"Unknown or unavailable growth reference: {stem!r}")
    provider, _ = entry
    if provider.download_resource is not None:
        provider.download_resource(filename)
    elif provider.initialize_data is not None:
        provider.initialize_data()
    else:
        raise DataError(f"No resource or acquisition policy for {provider.name}: {filename}")
    content = read_resource(filename)
    if content is None:
        raise DataError(f"Provider {provider.name} did not install verified {filename}")
    return content


def fetch_verified_source(url: str, sha256: str, *, limit: int = 15_000_000) -> bytes:
    """Fetch an audited HTTPS resource, enforcing bounded size and SHA-256."""
    if not url.startswith("https://") or len(sha256) != 64:
        raise DataError("Untrusted provider source URL or missing SHA-256")
    request = urllib.request.Request(  # noqa: S310 - only HTTPS is accepted above
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; pedgrowth/1.0; +https://github.com/erknet/pedgrowth)"
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:  # noqa: S310 - HTTPS only
            if not response.geturl().startswith("https://"):
                raise DataError("Provider redirected to an untrusted non-HTTPS source")
            length = response.headers.get("Content-Length")
            if length and int(length) > limit:
                raise DataError("Source file exceeds maximum download size")
            content = cast(bytes, response.read(limit + 1))
    except (OSError, ValueError) as exc:
        raise DataError(f"Cannot retrieve official reference {url}: {exc}") from exc
    if not content or len(content) > limit or hashlib.sha256(content).hexdigest() != sha256:
        raise DataError(f"Official reference source digest or size mismatch: {url}")
    return content


@contextmanager
def provider_write_lock(directory: Path) -> Any:
    """Cross-process exclusive lock around provider initialization."""
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / ".pedgrowth-download.lock"
    deadline = time.monotonic() + 60
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise DataError("Timed out waiting for reference download lock") from None
            time.sleep(0.1)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def save_verified_resource(directory: Path, name: str, content: bytes, expected: str) -> None:
    if not name or "/" in name or "\\" in name or hashlib.sha256(content).hexdigest() != expected:
        raise DataError(f"Unsafe or unverified provider output: {name}")
    directory.mkdir(parents=True, exist_ok=True)
    import tempfile

    descriptor, path = tempfile.mkstemp(dir=directory, prefix=".pedgrowth-", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(path, directory / name)
    finally:
        Path(path).unlink(missing_ok=True)


def read_reference(name: str, suffix: str) -> bytes | None:
    if suffix not in (".csv", ".lmsb"):
        raise DataError(f"Unsupported reference format: {suffix!r}")
    return read_resource(name + suffix)


def _source_files(group: str) -> dict[str, str]:
    """Discover the checksum-pinned editable inputs for one installed extension."""
    provider = registry.provider(group)
    manifest = provider.manifest()
    return {
        **{name + ".csv": str(info["csv_sha256"]) for name, info in manifest.get("tables", {}).items()},
        **{filename: str(sha) for filename, sha in (provider.additional_resources or {}).items()},
    }


def _manifest() -> dict[str, Any]:
    """Aggregated read-only catalog from installed providers (not bundled with core)."""
    combined: dict[str, Any] = {"tables": {}}
    for provider in _providers():
        manifest = provider.manifest()
        combined["tables"].update(manifest.get("tables", {}))
    return combined


def installed_references() -> dict[str, bool]:
    result: dict[str, bool] = {}
    for provider in _providers():
        files = _source_files(provider.name)
        result[provider.name] = all(
            read_resource(filename) is not None
            or (filename.endswith(".csv") and read_resource(filename[:-4] + ".lmsb") is not None)
            for filename in files
        )
    return result


def install_reference_source(
    source: str,
    from_dir: Path,
    *,
    accept_source_terms: bool,
    destination: Path | None = None,
) -> int:
    if not accept_source_terms:
        raise ValueError(
            "Review source-specific terms of the original provider and explicitly accept them first"
        )
    files = _source_files(source)
    staged: dict[str, bytes] = {}
    for name, expected in files.items():
        path = Path(from_dir) / name
        if not path.is_file() or path.stat().st_size > 10_000_000:
            raise DataError(f"Missing or oversized source file: {path}")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise DataError(f"Reference source hash differs from audited manifest: {name}")
        if name.endswith(".csv"):
            from .reference_data import parse_lms_csv

            parse_lms_csv(io.StringIO(data.decode("utf-8-sig")), name[:-4])
        staged[name] = data
    folder = Path(destination) if destination is not None else reference_directory()
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in staged.items():
        tmp = folder / (name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(folder / name)
    from .tables.table import _load_coefficients

    _load_coefficients.cache_clear()
    return len(staged)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage installed extension reference data")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    install = commands.add_parser("install")
    install.add_argument("source", choices=[p.name for p in _providers()])
    install.add_argument("--from-dir", type=Path, required=True)
    install.add_argument("--accept-source-terms", action="store_true")
    args = parser.parse_args()
    if args.command == "list":
        for name, is_installed in installed_references().items():
            print(f"{name}: {'installed' if is_installed else 'not installed'}")
    else:
        count = install_reference_source(
            args.source, args.from_dir, accept_source_terms=args.accept_source_terms
        )
        print(f"Installed {count} verified files for {args.source}")


if __name__ == "__main__":
    main()
