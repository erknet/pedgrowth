"""Generic ordered reference-plan resolution.

Scientific age constraints, measurement adjustments and table preference belong
to installed extensions. The core never imports or implements a provider plan.
"""

from __future__ import annotations

import math
import warnings

from .architecture import AgeDefinition, Indicator, ResolvedReference, _months
from .exceptions import DataError, DataNotFoundError
from .registry import registry
from .tables import AGE_BASED_TYPES, ReferenceTable, Sex, TableType


class GrowthPlan:
    """Generic ordered selection over extension-provided reference families.

    Extensions subclass this and register their named plan factories.
    """

    def __init__(self, families: tuple[str, ...], *, mode: str | None = None):
        if not families or any(not isinstance(family, str) or not family for family in families):
            raise ValueError("Reference families must be nonempty names")
        self.families = families
        self.mode = mode
        # Metadata prototypes can report identifier, indicator and sex without
        # reading coefficients or triggering an upstream download.
        self._tables = {
            family: tuple(cls.__new__(cls) for cls in registry.tables(family)) for family in self.families
        }
        self._loaded: dict[str, ReferenceTable] = {}
        if not any(self._tables.values()):
            raise DataNotFoundError(f"No reference extension installed for {families!r}")

    def _materialize(self, prototype: ReferenceTable) -> ReferenceTable:
        name = prototype.get_file_name()
        if name not in self._loaded:
            self._loaded[name] = type(prototype)()
        return self._loaded[name]

    def _descriptors(self) -> tuple[ReferenceTable, ...]:
        """Describe registered references without loading scientific datasets."""
        return tuple(table for family in self.families for table in self._tables[family])

    def tables(self) -> tuple[ReferenceTable, ...]:
        """Explicitly enumerate loadable tables, warning about unavailable ones."""
        results = []
        for family in self.families:
            for prototype in self._tables[family]:
                try:
                    results.append(self._materialize(prototype))
                except DataError as exc:
                    warnings.warn(
                        f"Reference {prototype.get_file_name()} unavailable: {exc}; "
                        "the file will be retried on next access",
                        RuntimeWarning,
                        stacklevel=2,
                    )
        return tuple(results)

    def _selected_families(
        self, kind: TableType, age: float | None, definition: AgeDefinition | None
    ) -> tuple[str, ...]:
        """Override to enforce a clinical or other provider-specific rule."""
        return self.families

    def _resolve_row(
        self,
        *,
        indicator: Indicator | TableType | str,
        sex: Sex | str,
        age: float | None = None,
        age_definition: AgeDefinition | None = None,
        coordinate: float | None = None,
    ) -> ResolvedReference:
        from .pygrowup import _parse_sex

        kind = TableType(Indicator(indicator).value)
        selected_sex = _parse_sex(sex)
        if kind in AGE_BASED_TYPES:
            if age is None or age_definition is None:
                raise ValueError("Age and age_definition are required for age-based indicators")
            x = _months(float(age), age_definition)
        else:
            if coordinate is None:
                raise ValueError("Length/height coordinate is required")
            x = float(coordinate)
        if not math.isfinite(x) or x < 0 or (kind not in AGE_BASED_TYPES and x == 0):
            raise ValueError("Invalid reference coordinate")
        age_months = (
            _months(float(age), age_definition) if age is not None and age_definition is not None else None
        )
        missing: DataError | None = None
        for family in self._selected_families(kind, age, age_definition):
            for candidate in registry.candidates(family, kind, age_months, self.mode):
                corrected = x + candidate.coordinate_offset
                for table in self._tables.get(family, ()):
                    if table.get_table_type() is not candidate.kind:
                        continue
                    if table.get_table_sex() not in (None, selected_sex):
                        continue
                    if not registry.accept_table(family, table, kind, age_months, candidate.kind, self.mode):
                        continue
                    try:
                        loaded = self._materialize(table)
                    except DataError as exc:
                        missing = exc
                        warnings.warn(
                            f"Reference {table.get_file_name()} unavailable: {exc}; retry on next access",
                            RuntimeWarning,
                            stacklevel=2,
                        )
                        continue
                    if loaded.get_min_range() <= corrected <= loaded.get_max_range():
                        return ResolvedReference(loaded, corrected, candidate.measurement_offset)
        if missing is not None:
            raise missing
        raise DataNotFoundError(
            f"No eligible reference for {kind.value}, sex={selected_sex.value}, coordinate={x}"
        )

    def resolve(
        self,
        *,
        indicator: Indicator | TableType | str,
        sex: Sex | str,
        age: float | None = None,
        age_definition: AgeDefinition | None = None,
        coordinate: float | None = None,
    ) -> ResolvedReference:
        return self._resolve_row(
            indicator=indicator,
            sex=sex,
            age=age,
            age_definition=age_definition,
            coordinate=coordinate,
        )

    def _batch_family_masks(
        self,
        kind: TableType,
        age_months: object | None,
        definition: AgeDefinition | None,
        count: int,
    ) -> dict[str, object]:
        """An extension can restrict each family to an array of eligible rows."""
        return {family: True for family in self.families}

    def resolve_numpy(
        self,
        *,
        indicator: Indicator | str,
        sexes: object,
        ages: object | None,
        age_definition: AgeDefinition | None,
        coordinates: object | None,
    ) -> tuple[list[ResolvedReference | None], list[Exception | None]]:
        """Vectorize table selection by family, candidate, table, sex and domain.

        Provider eligibility is evaluated on NumPy arrays, never by calling
        the scalar resolver for each observation. Object construction occurs
        only after the selected masks are complete.
        """
        import numpy as np

        from .exceptions import InvalidSexError

        kind = TableType(Indicator(indicator).value)
        genders = np.asarray(sexes)
        if genders.ndim != 1:
            raise ValueError("sexes must be one-dimensional")
        count = len(genders)

        def vector(data: object | None, name: str) -> object | None:
            if data is None:
                return None
            arr = np.asarray(data, dtype=float)
            if arr.ndim == 0:
                return np.full(count, float(arr))
            if arr.shape != (count,):
                raise ValueError(f"{name} must match sexes")
            return arr

        age_values = vector(ages, "ages")
        coordinate_values = vector(coordinates, "coordinates")
        if kind in AGE_BASED_TYPES:
            if age_values is None or age_definition is None:
                raise ValueError("Age and age_definition are required for age-based indicators")
            x = np.asarray(age_values, dtype=float) * _months(1.0, age_definition)
        else:
            if coordinate_values is None:
                raise ValueError("Length/height coordinate is required")
            x = np.asarray(coordinate_values, dtype=float)
        age_months = (
            np.asarray(age_values, dtype=float) * _months(1.0, age_definition)
            if age_values is not None and age_definition is not None
            else None
        )

        # Normalization and sex eligibility are vectorized; only exceptional
        # invalid positions require individual error objects.
        normalized = np.char.upper(np.char.strip(genders.astype(str)))
        males = np.isin(normalized, ("M", "MALE"))
        females = np.isin(normalized, ("F", "FEMALE"))
        sex_valid = males | females
        sex_ids = np.where(males, "M", np.where(females, "F", ""))
        coordinate_valid = np.isfinite(x) & (x >= 0 if kind in AGE_BASED_TYPES else x > 0)
        unresolved = coordinate_valid & sex_valid

        results: list[ResolvedReference | None] = [None] * count
        failures: list[Exception | None] = [None] * count
        family_masks = self._batch_family_masks(kind, age_months, age_definition, count)

        for family in self.families:
            if not registry.supports_vectorized_policy(family):
                raise ValueError(
                    f"Reference provider {family!r} must supply batch policy hooks "
                    "for array selection; use a custom scalar ReferencePlan otherwise"
                )
            allowed = unresolved & np.asarray(family_masks.get(family, False), dtype=bool)
            if not np.any(allowed):
                continue
            for candidate in registry.batch_candidates(family, kind, age_months, self.mode):
                corrected = x + np.asarray(candidate.coordinate_offset, dtype=float)
                measurement_offset = np.broadcast_to(
                    np.asarray(candidate.measurement_offset, dtype=float), (count,)
                )
                for table in self._tables.get(family, ()):
                    if table.get_table_type() is not candidate.kind:
                        continue
                    permitted = registry.accept_batch(
                        family, table, kind, age_months, candidate.kind, self.mode
                    )
                    potentially_eligible = allowed & unresolved & np.asarray(permitted, dtype=bool)
                    table_sex = table.get_table_sex()
                    if table_sex is not None:
                        potentially_eligible &= sex_ids == table_sex.value
                    if not np.any(potentially_eligible):
                        continue
                    try:
                        loaded = self._materialize(table)
                    except DataError as exc:
                        warnings.warn(
                            f"Reference {table.get_file_name()} unavailable: {exc}; retry on next access",
                            RuntimeWarning,
                            stacklevel=2,
                        )
                        for position in np.flatnonzero(potentially_eligible):
                            failures[int(position)] = exc
                        continue
                    eligible = (
                        potentially_eligible
                        & (corrected >= loaded.get_min_range())
                        & (corrected <= loaded.get_max_range())
                    )
                    for position in np.flatnonzero(eligible):
                        i = int(position)
                        results[i] = ResolvedReference(
                            loaded, float(corrected[i]), float(measurement_offset[i])
                        )
                        failures[i] = None
                    unresolved[eligible] = False

        for row in range(count):
            if results[row] is not None:
                continue
            if not sex_valid[row]:
                failures[row] = InvalidSexError(f"Sex must be M/F or male/female: {genders[row]!r}")
            elif not coordinate_valid[row]:
                failures[row] = ValueError("Invalid reference coordinate")
            elif failures[row] is None:
                failures[row] = DataNotFoundError(f"No eligible reference for {kind.value} at row {row}")
        return results, failures
