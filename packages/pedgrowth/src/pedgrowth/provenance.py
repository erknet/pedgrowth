"""Provider-neutral immutable provenance records for installed reference plugins."""

from __future__ import annotations

from dataclasses import dataclass

from .registry import registry


@dataclass(frozen=True, slots=True)
class ReferenceProvenance:
    name: str
    standard: str
    reference_version: str
    source_url: str | None
    source_sha256: str | None
    data_sha256: str
    snapshot_date: str | None
    custom: bool = False


def bundled_references() -> dict[str, ReferenceProvenance]:
    result: dict[str, ReferenceProvenance] = {}
    for provider in registry.providers():
        manifest = provider.manifest()
        for name, info in manifest.get("tables", {}).items():
            result[name] = ReferenceProvenance(
                name=name,
                standard=str(info["standard"]),
                reference_version=str(info["reference_version"]),
                source_url=info.get("source_url"),
                source_sha256=info.get("source_sha256"),
                data_sha256=str(info["csv_sha256"]),
                snapshot_date=manifest.get("snapshot_date"),
            )
    return result
