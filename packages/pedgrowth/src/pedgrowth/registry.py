"""Provider-neutral registration and entry-point discovery for growth references.

Independent provider wheels advertise the pedgrowth.references entry-point group.
The core imports no WHO/CDC/INTERGROWTH modules and needs none installed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import metadata, resources
from typing import Any, cast

from .exceptions import DataError
from .tables.table import ReferenceTable, TableType


@dataclass(frozen=True, slots=True)
class ReferenceCandidate:
    """One eligible table kind and its provider-defined coordinate adjustments."""

    kind: TableType
    coordinate_offset: float = 0.0
    measurement_offset: float = 0.0


@dataclass(frozen=True)
class ReferenceBatchCandidate:
    """Vectorized provider proposal with scalar/array coordinate adjustments."""

    kind: TableType
    coordinate_offset: object = 0.0
    measurement_offset: object = 0.0


@dataclass(frozen=True)
class ReferenceProvider:
    name: str
    family: str
    module: str
    tables: tuple[type[ReferenceTable], ...] = ()
    plans: Mapping[str, Callable[[], object]] | None = None
    manifest_name: str = "SOURCES.json"
    additional_resources: Mapping[str, str] | None = None
    initialize_data: Callable[[], int] | None = None
    download_resource: Callable[[str], int] | None = None
    candidate_policy: (
        Callable[[TableType, float | None, str | None], tuple[ReferenceCandidate, ...]] | None
    ) = None
    accept_policy: Callable[[ReferenceTable, TableType, float | None, TableType, str | None], bool] | None = (
        None
    )
    batch_candidate_policy: (
        Callable[[TableType, object | None, str | None], tuple[ReferenceBatchCandidate, ...]] | None
    ) = None
    batch_accept_policy: (
        Callable[[ReferenceTable, TableType, object | None, TableType, str | None], object] | None
    ) = None

    def manifest(self) -> dict[str, Any]:
        import json

        return cast(
            dict[str, Any],
            json.loads(resources.files(self.module).joinpath("data", self.manifest_name).read_text()),
        )


class ReferenceRegistry:
    """Explicit registry with lazy entry-point discovery and duplicate rejection."""

    def __init__(self) -> None:
        self._providers: dict[str, ReferenceProvider] = {}
        self._discovered = False
        self._discovering = False

    def register(self, provider: ReferenceProvider) -> None:
        if not provider.name or not provider.module:
            raise ValueError("Provider name and module must be nonempty")
        if provider.name in self._providers:
            raise DataError(f"Duplicate reference provider {provider.name!r}")
        self._providers[provider.name] = provider

    def discover(self) -> None:
        if self._discovered or self._discovering:
            return
        self._discovering = True
        previous = dict(self._providers)
        try:
            for point in sorted(
                metadata.entry_points(group="pedgrowth.references"), key=lambda x: (x.name, x.value)
            ):
                registration = point.load()
                if not callable(registration):
                    raise DataError(f"Invalid growth reference registration entry point: {point.name}")
                registration(self)
            self._discovered = True
        except Exception:
            self._providers = previous
            raise
        finally:
            self._discovering = False

    def providers(self) -> tuple[ReferenceProvider, ...]:
        self.discover()
        return tuple(self._providers.values())

    def provider(self, name: str) -> ReferenceProvider:
        self.discover()
        if name not in self._providers:
            raise DataError(f"Reference extension {name!r} is not installed")
        return self._providers[name]

    def tables(self, family: str) -> tuple[type[ReferenceTable], ...]:
        self.discover()
        return tuple(cls for p in self._providers.values() if p.family == family for cls in p.tables)

    def candidates(
        self, family: str, kind: TableType, age_months: float | None, mode: str | None
    ) -> tuple[ReferenceCandidate, ...]:
        self.discover()
        for provider in self._providers.values():
            if provider.family == family and provider.candidate_policy is not None:
                return provider.candidate_policy(kind, age_months, mode)
        return (ReferenceCandidate(kind),)

    def accept_table(
        self,
        family: str,
        table: ReferenceTable,
        kind: TableType,
        age_months: float | None,
        target: TableType,
        mode: str | None,
    ) -> bool:
        self.discover()
        for provider in self._providers.values():
            if provider.family == family and provider.accept_policy is not None:
                return provider.accept_policy(table, kind, age_months, target, mode)
        return True

    def supports_vectorized_policy(self, family: str) -> bool:
        """An extension supplying scalar rules must also supply array rules to vectorize."""
        self.discover()
        return all(
            (provider.candidate_policy is None or provider.batch_candidate_policy is not None)
            and (provider.accept_policy is None or provider.batch_accept_policy is not None)
            for provider in self._providers.values()
            if provider.family == family
        )

    def batch_candidates(
        self, family: str, kind: TableType, age_months: object | None, mode: str | None
    ) -> tuple[ReferenceBatchCandidate, ...]:
        self.discover()
        for provider in self._providers.values():
            if provider.family == family and provider.batch_candidate_policy is not None:
                return provider.batch_candidate_policy(kind, age_months, mode)
        return (ReferenceBatchCandidate(kind),)

    def accept_batch(
        self,
        family: str,
        table: ReferenceTable,
        kind: TableType,
        age_months: object | None,
        target: TableType,
        mode: str | None,
    ) -> object:
        self.discover()
        for provider in self._providers.values():
            if provider.family == family and provider.batch_accept_policy is not None:
                return provider.batch_accept_policy(table, kind, age_months, target, mode)
        return True

    def plans(self) -> dict[str, Callable[[], object]]:
        self.discover()
        found: dict[str, Callable[[], object]] = {}
        for provider in self._providers.values():
            for name, factory in (provider.plans or {}).items():
                if name in found:
                    raise DataError(f"Duplicate registered plan name: {name}")
                found[name] = factory
        return found

    def plan(self, name: str) -> object:
        return self.plans()[name]()

    def reset(self) -> None:
        """Reset explicitly for isolated tests. Never unload installed packages."""
        self._providers.clear()
        self._discovered = False


registry = ReferenceRegistry()


def available_plans() -> tuple[str, ...]:
    return tuple(sorted(registry.plans()))


def create_plan(name: str) -> object:
    return registry.plan(name)


def available_providers() -> tuple[str, ...]:
    return tuple(p.name for p in registry.providers())
