"""Public pediatric anthropometry calculator (WHO and optional CDC)."""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast, overload

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import ArrayLike, NDArray

from . import exceptions
from .architecture import (
    AgeDefinition,
    GrowthResult,
    Indicator,
    ReferencePlan,
    ResolvedReference,
)
from .extra_tables import CsvGrowthTable, TableDefinition
from .policies import InterpolationPolicy, MeasurementPosition, ReferenceStandard
from .provenance import ReferenceProvenance
from .registry import registry
from .tables import (
    AGE_BASED_TYPES,
    LENGTH_BASED_TYPES,
    TYPES_ALIASES,
    GrowthTable,
    ReferenceTable,
    Sex,
    TableType,
)

HEIGHT_TO_LENGTH_FACTOR = 0.7  # centimeters


def _positive_number(
    value: float | int | str | None, error_type: type[Exception], *, allow_zero: bool = False
) -> float:
    if isinstance(value, bool):
        raise error_type(f"Invalid number: {value!r}")
    try:
        if value is None:
            raise error_type("None cannot be interpreted as a number")
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise error_type(f"Invalid number: {value!r}") from exc
    if not math.isfinite(result) or (result < 0 if allow_zero else result <= 0):
        raise error_type(f"Invalid number: {value!r}")
    return result


def _parse_sex(sex: Sex | str) -> Sex:
    if isinstance(sex, Sex):
        return sex
    if isinstance(sex, str):
        value = {
            "M": Sex.Male,
            "MALE": Sex.Male,
            "F": Sex.Female,
            "FEMALE": Sex.Female,
        }.get(sex.strip().upper())
        if value is not None:
            return value
    raise exceptions.InvalidSexError(f"Sex must be M/F or male/female: {sex!r}")


def _parse_indicator(indicator: TableType | str) -> TableType:
    if isinstance(indicator, TableType):
        return indicator
    if isinstance(indicator, str):
        for kind in TableType:
            if kind.value == indicator.strip().lower():
                return kind
    raise exceptions.InvalidTableNameError(f"Unknown growth indicator: {indicator!r}")


def _recumbent_flag(
    legacy_flag: bool,
    position: MeasurementPosition | str | None,
) -> bool:
    if position is None:
        return legacy_flag
    selected = MeasurementPosition(position)
    if legacy_flag and selected is MeasurementPosition.STANDING:
        raise ValueError("Conflicting measurement position arguments")
    return selected is MeasurementPosition.RECUMBENT


class GrowthChartsCalculator:
    """Calculate sex-specific growth z-scores from WHO and/or CDC reference data.

    Age coordinates are in months (using 30.4375 days per month for WHO).
    Length, height, and head circumference are in cm; weight is in kg.

    Legacy defaults use WHO only. Set include_cdc=True to enable WHO-first
    CDC fallback, or use an explicit plan/table for typed selection. For
    CDC-only legacy calculations, set standard='cdc'.
    """

    def __init__(
        self,
        adjust_height_data: bool = False,
        include_cdc: bool = False,
        override_tables: Sequence[type[GrowthTable]] | None = None,
        *,
        table_overrides: Mapping[str, str | Path] | None = None,
        standard: ReferenceStandard | str | None = None,
        interpolation: InterpolationPolicy | str = InterpolationPolicy.NEAREST,
        additional_tables: Sequence[TableDefinition] = (),
        plan: ReferencePlan | None = None,
        table: ReferenceTable | None = None,
    ) -> None:
        if plan is not None and table is not None:
            raise ValueError("Specify either plan or table")
        if (plan is not None or table is not None) and (
            standard is not None
            or include_cdc
            or override_tables is not None
            or additional_tables
            or table_overrides
        ):
            raise ValueError("Explicit plan/table cannot be combined with legacy reference configuration")
        self.plan = plan
        self.direct_table = table
        self.adjust_height_data = adjust_height_data
        self.interpolation = InterpolationPolicy(interpolation)
        self.standard = (
            ReferenceStandard(standard)
            if standard is not None
            else (ReferenceStandard.WHO_THEN_CDC if include_cdc else ReferenceStandard.WHO)
        )
        if standard is not None and include_cdc:
            raise ValueError("Specify either standard= or include_cdc=, not both")
        if override_tables is not None and standard is not None:
            raise ValueError("Cannot combine standard= with override_tables=")

        def registered_lms(family: str) -> list[type[GrowthTable]]:
            from .tables.table import GrowthTable

            classes = registry.tables(family)
            if not all(issubclass(cls, GrowthTable) for cls in classes):
                raise exceptions.DataError("Legacy LMS selection requires LMS-backed extension tables")
            return [cast(type[GrowthTable], cls) for cls in classes]

        selected: Sequence[Callable[[], GrowthTable]]
        if plan is not None or table is not None:
            selected = []
        elif override_tables is not None:
            selected = list(override_tables)
        elif self.standard is ReferenceStandard.WHO:
            selected = registered_lms("who")
        elif self.standard is ReferenceStandard.CDC:
            selected = registered_lms("cdc")
        elif self.standard is ReferenceStandard.WHO_THEN_CDC:
            selected = [*registered_lms("who"), *registered_lms("cdc")]
        else:
            selected = [*registered_lms("cdc"), *registered_lms("who")]
        names = [definition.name for definition in additional_tables]
        if len(set(names)) != len(names):
            raise exceptions.DataError("Duplicate additional table names")

        def deferred_resolver(factory: Callable[[], GrowthTable]) -> GrowthTable:
            if isinstance(factory, type) and issubclass(factory, GrowthTable):
                return object.__new__(factory)
            return cast(GrowthTable, factory())

        self._resolvers: list[GrowthTable] = [
            *(CsvGrowthTable(definition) for definition in additional_tables),
            *(deferred_resolver(factory) for factory in selected),
        ]
        self._materialized_tables: dict[str, GrowthTable] = {
            table.get_file_name(): table for table in self._resolvers if isinstance(table, CsvGrowthTable)
        }
        if not self._resolvers and self.plan is None and self.direct_table is None:
            raise exceptions.DataError(
                "Reference provider not installed or enabled. Install a provider plugin, "
                "or supply an explicit plan or table."
            )
        table_names = [table.get_file_name() for table in self._resolvers]
        if len(set(table_names)) != len(table_names):
            raise exceptions.DataError("Duplicate reference identifiers; use table_overrides for replacement")
        # CSV overrides affect only this GrowthChartsCalculator; bundled cached data stay unchanged.
        overrides = dict(table_overrides or {})
        available = {table.get_file_name() for table in self._resolvers}
        unknown = set(overrides) - available
        if unknown:
            raise exceptions.DataError(f"Unknown or disabled reference tables: {sorted(unknown)!r}")
        self.table_override_hashes: dict[str, str] = {}
        for table in self._resolvers:
            name = table.get_file_name()
            if name in overrides:
                # User-provided overrides initialize just their own table.
                table.use_csv_override(overrides[name])
                self._materialized_tables[name] = table
                checksum = table.override_sha256
                if checksum is None:
                    raise exceptions.DataError(f"Override lacks SHA-256 provenance: {name}")
                self.table_override_hashes[name] = checksum
        candidate_tables: list[ReferenceTable] = [*self._resolvers]
        if self.plan is not None:
            from .plans import GrowthPlan

            if not isinstance(self.plan, GrowthPlan):
                candidate_tables.extend(self.plan.tables())
        if self.direct_table is not None:
            candidate_tables.append(self.direct_table)
        self.table_source_hashes: dict[str, str] = {
            source.get_file_name(): source.override_sha256
            for source in candidate_tables
            if isinstance(source, CsvGrowthTable) and source.override_sha256 is not None
        }
        self._by_type: dict[TableType, tuple[GrowthTable, ...]] = {
            kind: tuple(table for table in self._resolvers if table.get_table_type() is kind)
            for kind in TableType
        }

    def resolve(
        self,
        *,
        indicator: Indicator | TableType | str,
        sex: Sex | str,
        age: float | None = None,
        age_definition: AgeDefinition | None = None,
        coordinate: float | None = None,
    ) -> ResolvedReference:
        """Resolve a single reference without evaluating the measurement."""
        from .architecture import _months

        kind = TableType(Indicator(indicator).value)
        selected_sex = _parse_sex(sex)
        if self.direct_table is not None:
            table = self.direct_table
            if table.get_table_type() != kind:
                raise exceptions.DataNotFoundError("Direct table does not support requested indicator")
            if table.get_table_sex() not in (None, selected_sex):
                raise exceptions.DataNotFoundError("Direct table does not support requested sex")
            if kind in AGE_BASED_TYPES and age is not None and age_definition is not None:
                age_converter = getattr(table, "age_coordinate", None)
                if callable(age_converter):
                    x = age_converter(float(age), age_definition)
                else:
                    x = _months(float(age), age_definition)
            else:
                x = coordinate
            if x is None:
                raise ValueError("Required age definition or coordinate is missing")
            if not table.get_min_range() <= x <= table.get_max_range():
                raise exceptions.DataNotFoundError("Coordinate outside direct table domain")
            return ResolvedReference(table, float(x))
        if self.plan is not None:
            return self.plan.resolve(
                indicator=kind.value,
                sex=selected_sex,
                age=age,
                age_definition=age_definition,
                coordinate=coordinate,
            )
        from .architecture import _months

        x = (
            _months(float(age), age_definition)
            if kind in AGE_BASED_TYPES and age is not None and age_definition is not None
            else coordinate
        )
        if x is None:
            raise ValueError("Required age definition or coordinate is missing")
        legacy_table = self.find_table(kind, selected_sex, float(x))
        if legacy_table is None:
            raise exceptions.DataNotFoundError("No matching growth reference")
        return ResolvedReference(legacy_table, float(x))

    def calculate(
        self,
        *,
        indicator: Indicator | TableType | str,
        measurement: float,
        sex: Sex | str,
        age: float | None = None,
        age_definition: AgeDefinition | None = None,
        coordinate: float | None = None,
    ) -> GrowthResult:
        """Evaluate one measurement, retaining the selected reference identity."""
        selected = self.resolve(
            indicator=indicator, sex=sex, age=age, age_definition=age_definition, coordinate=coordinate
        )
        value = _positive_number(measurement, exceptions.InvalidMeasurement)
        adjusted_measurement = value + selected.measurement_offset
        if adjusted_measurement <= 0:
            raise exceptions.InvalidMeasurement("Position-adjusted measurement must be positive")
        z = selected.table.calculate_zscore(
            selected.coordinate,
            adjusted_measurement,
            _parse_sex(sex),
            interpolation=self.interpolation,
        )
        return GrowthResult(z, selected.reference_id)

    def zscore(
        self,
        *,
        indicator: Indicator | TableType | str,
        measurement: float,
        sex: Sex | str,
        age: float | None = None,
        age_definition: AgeDefinition | None = None,
        coordinate: float | None = None,
    ) -> float:
        """Typed scalar entry point."""
        return self.calculate(
            indicator=indicator,
            measurement=measurement,
            sex=sex,
            age=age,
            age_definition=age_definition,
            coordinate=coordinate,
        ).zscore

    def calculate_numpy(
        self,
        *,
        indicator: Indicator | str,
        measurements: object,
        sexes: object,
        ages: object | None = None,
        age_definition: AgeDefinition | None = None,
        coordinates: object | None = None,
        errors: str = "raise",
    ) -> tuple[object, object]:
        """Optional NumPy evaluation returning (z-scores, reference IDs)."""
        from .execution import calculate_numpy

        return calculate_numpy(
            self,
            indicator=indicator,
            measurements=measurements,
            sexes=sexes,
            ages=ages,
            age_definition=age_definition,
            coordinates=coordinates,
            errors=errors,
        )

    def available_references(self) -> dict[str, ReferenceProvenance]:
        """Describe every enabled reference and its data provenance."""
        from .provenance import bundled_references

        bundled = bundled_references()
        result: dict[str, ReferenceProvenance] = {}
        selected_references: list[ReferenceTable]
        if self.plan is not None:
            from .plans import GrowthPlan

            selected_references = list(
                self.plan._descriptors() if isinstance(self.plan, GrowthPlan) else self.plan.tables()
            )
        elif self.direct_table is not None:
            selected_references = [self.direct_table]
        else:
            selected_references = list(self._resolvers)
        for table in selected_references:
            name = table.get_file_name()
            explicitly_provided = table.get_provenance()
            if explicitly_provided is not None:
                result[name] = explicitly_provided
            elif name in self.table_source_hashes or name in self.table_override_hashes:
                definition = table._definition if isinstance(table, CsvGrowthTable) else None
                result[name] = ReferenceProvenance(
                    name=name,
                    standard=definition.standard_name if definition else "custom override",
                    reference_version=definition.reference_version if definition else "user-supplied",
                    source_url=definition.source_url if definition else None,
                    source_sha256=None,
                    data_sha256=self.table_source_hashes.get(name, self.table_override_hashes.get(name, "")),
                    snapshot_date=None,
                    custom=True,
                )
            elif name in bundled:
                result[name] = bundled[name]
            else:
                raise exceptions.DataError(
                    f"Missing provenance for reference {name}; custom ReferenceTable classes "
                    "should implement get_provenance()"
                )
        return result

    def reference_for(
        self, indicator: TableType | str, index_value: float, sex: Sex | str
    ) -> ReferenceProvenance:
        """Identify the selected reference for a given indicator, index and sex."""
        table = self.find_table(_parse_indicator(indicator), _parse_sex(sex), index_value)
        if table is None:
            raise exceptions.DataNotFoundError("No matching growth reference")
        return self.available_references()[table.get_file_name()]

    @overload
    def lhfa(
        self,
        measurement: float | str | None,
        age_in_months: float | str,
        sex: str | Sex,
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> float | None: ...

    @overload
    def lhfa(
        self,
        measurement: NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> NDArray[np.float64]: ...

    @overload
    def lhfa(
        self,
        measurement: float | str,
        age_in_months: NDArray[Any],
        sex: str | Sex,
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> NDArray[np.float64]: ...

    def lhfa(
        self,
        measurement: float | str | None | NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> float | None | NDArray[np.float64]:
        """Length or height (cm) for age (months)."""
        return self.zscore_for_measurement(
            TableType.LengthForAge, measurement, sex, age_in_months, is_recumbent_height, position=position
        )

    @overload
    def wfl(
        self,
        measurement: float | str | None,
        sex: str | Sex,
        length: float | str,
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> float | None: ...

    @overload
    def wfl(
        self,
        measurement: NDArray[Any],
        sex: str | Sex,
        length: float | str | NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> NDArray[np.float64]: ...

    @overload
    def wfl(
        self,
        measurement: float | str,
        sex: str | Sex,
        length: NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> NDArray[np.float64]: ...

    def wfl(
        self,
        measurement: float | str | None | NDArray[Any],
        sex: str | Sex,
        length: float | str | NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> float | None | NDArray[np.float64]:
        """Weight (kg) for recumbent length (cm)."""
        return self.zscore_for_measurement(
            TableType.WeightForLength, measurement, sex, length, is_recumbent_height, position=position
        )

    @overload
    def wfh(
        self,
        measurement: float | str | None,
        sex: str | Sex,
        height: float | str,
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> float | None: ...

    @overload
    def wfh(
        self,
        measurement: NDArray[Any],
        sex: str | Sex,
        height: float | str | NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> NDArray[np.float64]: ...

    @overload
    def wfh(
        self,
        measurement: float | str,
        sex: str | Sex,
        height: NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> NDArray[np.float64]: ...

    def wfh(
        self,
        measurement: float | str | None | NDArray[Any],
        sex: str | Sex,
        height: float | str | NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> float | None | NDArray[np.float64]:
        """Weight (kg) for standing height (cm)."""
        return self.zscore_for_measurement(
            TableType.WeightForHeight, measurement, sex, height, is_recumbent_height, position=position
        )

    @overload
    def wfa(
        self,
        measurement: float | str | None,
        age_in_months: float | str,
        sex: str | Sex,
    ) -> float | None: ...

    @overload
    def wfa(
        self,
        measurement: NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
    ) -> NDArray[np.float64]: ...

    @overload
    def wfa(
        self,
        measurement: float | str,
        age_in_months: NDArray[Any],
        sex: str | Sex,
    ) -> NDArray[np.float64]: ...

    def wfa(
        self,
        measurement: float | str | None | NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
    ) -> float | None | NDArray[np.float64]:
        """Weight (kg) for age (months)."""
        return self.zscore_for_measurement(TableType.WeightForAge, measurement, sex, age_in_months)

    @overload
    def bmifa(
        self,
        measurement: float | str | None,
        age_in_months: float | str,
        sex: str | Sex,
    ) -> float | None: ...

    @overload
    def bmifa(
        self,
        measurement: NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
    ) -> NDArray[np.float64]: ...

    @overload
    def bmifa(
        self,
        measurement: float | str,
        age_in_months: NDArray[Any],
        sex: str | Sex,
    ) -> NDArray[np.float64]: ...

    def bmifa(
        self,
        measurement: float | str | None | NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
    ) -> float | None | NDArray[np.float64]:
        """BMI (kg/m²) for age (months)."""
        return self.zscore_for_measurement(TableType.BodyMassIndexForAge, measurement, sex, age_in_months)

    @overload
    def hcfa(
        self,
        measurement: float | str | None,
        age_in_months: float | str,
        sex: str | Sex,
    ) -> float | None: ...

    @overload
    def hcfa(
        self,
        measurement: NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
    ) -> NDArray[np.float64]: ...

    @overload
    def hcfa(
        self,
        measurement: float | str,
        age_in_months: NDArray[Any],
        sex: str | Sex,
    ) -> NDArray[np.float64]: ...

    def hcfa(
        self,
        measurement: float | str | None | NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
    ) -> float | None | NDArray[np.float64]:
        """Head circumference (cm) for age (months)."""
        return self.zscore_for_measurement(TableType.HeadCircumferenceForAge, measurement, sex, age_in_months)

    @overload
    def muacfa(
        self, measurement: float | str | None, age_in_months: float | str, sex: str | Sex
    ) -> float | None: ...

    @overload
    def muacfa(
        self, measurement: NDArray[Any], age_in_months: float | str | NDArray[Any], sex: str | Sex
    ) -> NDArray[np.float64]: ...

    @overload
    def muacfa(
        self, measurement: float | str, age_in_months: NDArray[Any], sex: str | Sex
    ) -> NDArray[np.float64]: ...

    def muacfa(
        self,
        measurement: float | str | None | NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
    ) -> float | None | NDArray[np.float64]:
        """Mid-upper arm circumference (cm) for age; WHO 3–60 months."""
        return self.zscore_for_measurement(
            TableType.MidUpperArmCircumferenceForAge, measurement, sex, age_in_months
        )

    @overload
    def tsfa(
        self, measurement: float | str | None, age_in_months: float | str, sex: str | Sex
    ) -> float | None: ...

    @overload
    def tsfa(
        self, measurement: NDArray[Any], age_in_months: float | str | NDArray[Any], sex: str | Sex
    ) -> NDArray[np.float64]: ...

    @overload
    def tsfa(
        self, measurement: float | str, age_in_months: NDArray[Any], sex: str | Sex
    ) -> NDArray[np.float64]: ...

    def tsfa(
        self,
        measurement: float | str | None | NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
    ) -> float | None | NDArray[np.float64]:
        """Triceps skinfold thickness (mm) for age; WHO 3–60 months."""
        return self.zscore_for_measurement(TableType.TricepsSkinfoldForAge, measurement, sex, age_in_months)

    @overload
    def ssfa(
        self, measurement: float | str | None, age_in_months: float | str, sex: str | Sex
    ) -> float | None: ...

    @overload
    def ssfa(
        self, measurement: NDArray[Any], age_in_months: float | str | NDArray[Any], sex: str | Sex
    ) -> NDArray[np.float64]: ...

    @overload
    def ssfa(
        self, measurement: float | str, age_in_months: NDArray[Any], sex: str | Sex
    ) -> NDArray[np.float64]: ...

    def ssfa(
        self,
        measurement: float | str | None | NDArray[Any],
        age_in_months: float | str | NDArray[Any],
        sex: str | Sex,
    ) -> float | None | NDArray[np.float64]:
        """Subscapular skinfold thickness (mm) for age; WHO 3–60 months."""
        return self.zscore_for_measurement(
            TableType.SubscapularSkinfoldForAge, measurement, sex, age_in_months
        )

    def _load_matching_table(self, prototype: GrowthTable) -> GrowthTable:
        """Materialize a reference only when its indicator and sex are accessed."""
        name = prototype.get_file_name()
        loaded = self._materialized_tables.get(name)
        if loaded is None:
            loaded = type(prototype)()
            self._materialized_tables[name] = loaded
        return loaded

    def find_table(
        self,
        indicator: TableType,
        sex: Sex,
        index_value: float,
        aliases_included: bool = False,
    ) -> GrowthTable | None:
        """Find the first applicable reference table, preserving the legacy ordering."""
        missing: exceptions.DataError | None = None
        for prototype in self._by_type.get(indicator, ()):
            if prototype.get_table_sex() not in (None, sex):
                continue
            try:
                table = self._load_matching_table(prototype)
            except exceptions.DataError as exc:
                missing = exc
                warnings.warn(
                    f"Reference {prototype.get_file_name()} unavailable: {exc}; retry on next access",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            if table.get_min_range() <= index_value <= table.get_max_range():
                return table
        if missing is not None:
            raise missing
        if not aliases_included and indicator in TYPES_ALIASES:
            return self.find_table(TYPES_ALIASES[indicator], sex, index_value, aliases_included=True)
        return None

    def zscores_numpy(
        self,
        indicator: TableType | str,
        measurements: ArrayLike,
        index_values: ArrayLike,
        sex: Sex | str,
        *,
        is_recumbent_height: bool = False,
        position: MeasurementPosition | str | None = None,
    ) -> NDArray[np.float64]:
        """Vectorized bulk LMS z-scores using optional NumPy and SciPy.

        Install with `pip install pedgrowth[vector]`.
        Inputs must be equally sized one-dimensional real numeric arrays.
        The return value is a NumPy float64 array.
        """
        if self.plan is not None or self.direct_table is not None:
            raise ValueError("Use calculate_numpy() with explicit age_definition for plan/table calculators")
        try:
            from .batch import calculate_many
        except ImportError as exc:
            raise ImportError(
                "Vectorized evaluation requires NumPy and SciPy: pip install pedgrowth[vector]"
            ) from exc
        return calculate_many(
            self,
            _parse_indicator(indicator),
            measurements,
            index_values,
            _parse_sex(sex),
            is_recumbent_height=_recumbent_flag(is_recumbent_height, position),
        )

    @overload
    def zscore_for_measurement(
        self,
        indicator: TableType | str,
        measurement: float | str | None,
        sex: Sex | str,
        index_value: float | str,
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> float | None: ...

    @overload
    def zscore_for_measurement(
        self,
        indicator: TableType | str,
        measurement: NDArray[Any],
        sex: Sex | str,
        index_value: float | str | NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> NDArray[np.float64]: ...

    @overload
    def zscore_for_measurement(
        self,
        indicator: TableType | str,
        measurement: float | str,
        sex: Sex | str,
        index_value: NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> NDArray[np.float64]: ...

    @overload
    def zscore_for_measurement(
        self,
        indicator: TableType | str,
        measurement: float | str | None | NDArray[Any],
        sex: Sex | str,
        index_value: float | str | NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> float | None | NDArray[np.float64]: ...

    def zscore_for_measurement(
        self,
        indicator: TableType | str,
        measurement: float | str | None | NDArray[Any],
        sex: Sex | str,
        index_value: float | str | NDArray[Any],
        is_recumbent_height: bool = False,
        *,
        position: MeasurementPosition | str | None = None,
    ) -> float | None | NDArray[np.float64]:
        """Calculate a z-score; None measurement returns None.

        Raises InvalidMeasurement, InvalidSexError, InvalidAgeError,
        InvalidLengthError, InvalidTableNameError, or DataNotFoundError.
        """
        if self.plan is not None or self.direct_table is not None:
            raise ValueError("Use zscore() with explicit age_definition for plan/table calculators")
        if measurement is None:
            return None

        # Dispatch only array-like numerical inputs; scalar calls avoid NumPy
        # imports entirely and retain their historical return types.
        array_input = any(
            getattr(value, "ndim", 0) > 0 and hasattr(value, "__array__")
            for value in (measurement, index_value)
        )
        if array_input:
            return self.zscores_numpy(
                indicator,
                measurement,
                index_value,
                sex,
                is_recumbent_height=is_recumbent_height,
                position=position,
            )

        sex_value = _parse_sex(sex)
        indicator_value = _parse_indicator(indicator)

        index_error: type[Exception]
        if indicator_value in LENGTH_BASED_TYPES:
            index_error = exceptions.InvalidLengthError
        elif indicator_value in AGE_BASED_TYPES:
            index_error = exceptions.InvalidAgeError
        else:
            index_error = exceptions.InvalidIndexError
        index = _positive_number(
            cast("float | str", index_value),
            index_error,
            allow_zero=indicator_value in AGE_BASED_TYPES,
        )
        measured = _positive_number(cast("float | str", measurement), exceptions.InvalidMeasurement)

        table = self.find_table(indicator_value, sex_value, index)
        if table is None:
            raise exceptions.DataNotFoundError(
                f"No reference for indicator={indicator_value.value}, sex={sex_value.value}, index={index}"
            )

        is_recumbent_height = _recumbent_flag(is_recumbent_height, position)
        if self.adjust_height_data:
            if table.get_table_type() == TableType.HeightForAge and is_recumbent_height:
                measured -= HEIGHT_TO_LENGTH_FACTOR
            elif table.get_table_type() == TableType.LengthForAge and not is_recumbent_height:
                measured += HEIGHT_TO_LENGTH_FACTOR
            elif table.get_table_type() == TableType.WeightForHeight and is_recumbent_height:
                index -= HEIGHT_TO_LENGTH_FACTOR
            elif table.get_table_type() == TableType.WeightForLength and not is_recumbent_height:
                index += HEIGHT_TO_LENGTH_FACTOR
            if measured <= 0:
                raise exceptions.InvalidMeasurement("Adjusted length/height must remain positive")

        return table.calculate_zscore(index, measured, sex_value, interpolation=self.interpolation)
