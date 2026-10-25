"""Shared reference contracts and age/indicator types (no plan implementation)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .tables import Sex, TableType
from .tables.table import ReferenceTable


class Indicator(StrEnum):
    BMI_FOR_AGE = "bmifa"
    MUAC_FOR_AGE = "muacfa"
    TRICEPS_SKINFOLD_FOR_AGE = "tsfa"
    SUBSCAPULAR_SKINFOLD_FOR_AGE = "ssfa"
    HEAD_CIRCUMFERENCE_FOR_AGE = "hcfa"
    LENGTH_FOR_AGE = "lfa"
    HEIGHT_FOR_AGE = "hfa"
    WEIGHT_FOR_AGE = "wfa"
    WEIGHT_FOR_HEIGHT = "wfh"
    WEIGHT_FOR_LENGTH = "wfl"


class AgeUnit(StrEnum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class CoordinateType(StrEnum):
    AGE = "age"
    LENGTH = "length"
    HEIGHT = "height"


class AgeType(StrEnum):
    CHRONOLOGICAL = "chronological"
    GESTATIONAL = "gestational"
    POSTMENSTRUAL = "postmenstrual"
    CORRECTED = "corrected"


@dataclass(frozen=True, slots=True)
class AgeDefinition:
    type: AgeType
    unit: AgeUnit

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", AgeType(self.type))
        object.__setattr__(self, "unit", AgeUnit(self.unit))


@dataclass(frozen=True, slots=True)
class TableDomain:
    indicator: Indicator
    minimum: float
    maximum: float
    coordinate_type: CoordinateType
    sex: Sex | None = None


@dataclass(frozen=True, slots=True)
class GrowthResult:
    zscore: float
    reference_id: str


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    table: ReferenceTable
    coordinate: float
    measurement_offset: float = 0.0

    @property
    def reference_id(self) -> str:
        return self.table.get_file_name()

    @property
    def domain(self) -> TableDomain:
        indicator = Indicator(self.table.get_table_type().value)
        coordinate_type = (
            CoordinateType.LENGTH
            if indicator is Indicator.WEIGHT_FOR_LENGTH
            else CoordinateType.HEIGHT
            if indicator is Indicator.WEIGHT_FOR_HEIGHT
            else CoordinateType.AGE
        )
        return TableDomain(
            indicator,
            self.table.get_min_range(),
            self.table.get_max_range(),
            coordinate_type,
            self.table.get_table_sex(),
        )


def _months(value: float, definition: AgeDefinition) -> float:
    if definition.type is not AgeType.CHRONOLOGICAL:
        raise ValueError("WHO/CDC postnatal references require chronological age")
    factors = {
        AgeUnit.DAYS: 1 / 30.4375,
        AgeUnit.WEEKS: 7 / 30.4375,
        AgeUnit.MONTHS: 1.0,
        AgeUnit.YEARS: 12.0,
    }
    return value * factors[definition.unit]


class ReferencePlan(Protocol):
    """Plug a reference-selection policy into the engine.

    tables() supplies provenance enumeration; resolve() selects a
    reference and coordinate/measurement offsets for an observation.
    """

    def resolve(
        self,
        *,
        indicator: Indicator | TableType | str,
        sex: Sex | str,
        age: float | None = None,
        age_definition: AgeDefinition | None = None,
        coordinate: float | None = None,
    ) -> ResolvedReference: ...

    def tables(self) -> tuple[ReferenceTable, ...]: ...
