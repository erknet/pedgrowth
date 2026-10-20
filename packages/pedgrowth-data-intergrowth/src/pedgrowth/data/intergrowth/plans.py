"""INTERGROWTH-specific postmenstrual age selection."""

from __future__ import annotations

import math

from pedgrowth.architecture import AgeDefinition, AgeType, AgeUnit, Indicator, ResolvedReference
from pedgrowth.exceptions import DataNotFoundError
from pedgrowth.pygrowup import _parse_sex
from pedgrowth.tables import AGE_BASED_TYPES, Sex, TableType
from pedgrowth.tables.table import ReferenceTable


class IntergrowthPlan:
    """INTERGROWTH preterm postnatal only; birth/fetal references require direct selection."""

    def __init__(self) -> None:
        from .intergrowth_tables import INTERGROWTH_POSTNATAL_TABLES

        self._tables = tuple(cls() for cls in INTERGROWTH_POSTNATAL_TABLES)

    def tables(self) -> tuple[ReferenceTable, ...]:
        """List the eligible postnatal reference equations."""
        return self._tables

    def resolve_numpy(
        self,
        *,
        indicator: Indicator | str,
        sexes: object,
        ages: object | None,
        age_definition: AgeDefinition | None,
        coordinates: object | None,
    ) -> tuple[list[ResolvedReference | None], list[Exception | None]]:
        """Vectorized INTERGROWTH PMA, sex and table-domain selection."""
        import numpy as np
        from pedgrowth.exceptions import InvalidSexError

        kind = TableType(Indicator(indicator).value)
        genders = np.asarray(sexes)
        if genders.ndim != 1:
            raise ValueError("sexes must be one-dimensional")
        count = len(genders)
        if ages is None or age_definition is None or age_definition.type is not AgeType.POSTMENSTRUAL:
            raise ValueError("INTERGROWTH postnatal plans require postmenstrual age for all indicators")

        def vector(value: object | None, name: str) -> object | None:
            if value is None:
                return None
            array = np.asarray(value, dtype=float)
            if array.ndim == 0:
                return np.full(count, float(array))
            if array.shape != (count,):
                raise ValueError(f"{name} must match sexes")
            return array

        age_array = np.asarray(vector(ages, "ages"), dtype=float)
        factor = {
            AgeUnit.DAYS: 1 / 7,
            AgeUnit.WEEKS: 1,
            AgeUnit.MONTHS: 30.4375 / 7,
            AgeUnit.YEARS: 365.25 / 7,
        }[age_definition.unit]
        pma = age_array * factor
        if kind in AGE_BASED_TYPES:
            x = pma
        else:
            if coordinates is None:
                raise ValueError("INTERGROWTH weight-for-length requires length in cm")
            x = np.asarray(vector(coordinates, "coordinates"), dtype=float)
        sexes_normalized = np.char.upper(np.char.strip(genders.astype(str)))
        male = np.isin(sexes_normalized, ("M", "MALE"))
        female = np.isin(sexes_normalized, ("F", "FEMALE"))
        sex_valid = male | female
        valid_pma = np.isfinite(pma) & (pma >= 27) & (pma <= 64)
        valid_coordinate = np.isfinite(x)
        unresolved = sex_valid & valid_pma & valid_coordinate
        results: list[ResolvedReference | None] = [None] * count
        failures: list[Exception | None] = [None] * count
        for table in self._tables:
            if table.get_table_type() is not kind:
                continue
            eligible = unresolved & (x >= table.get_min_range()) & (x <= table.get_max_range())
            table_sex = table.get_table_sex()
            if table_sex is not None:
                eligible &= male if table_sex is Sex.Male else female
            for pos in np.flatnonzero(eligible):
                index = int(pos)
                results[index] = ResolvedReference(table, float(x[index]))
            unresolved[eligible] = False
        for row in range(count):
            if results[row] is not None:
                continue
            if not sex_valid[row]:
                failures[row] = InvalidSexError(f"Sex must be M/F or male/female: {genders[row]!r}")
            elif not valid_pma[row]:
                failures[row] = DataNotFoundError("INTERGROWTH postnatal plans require 27–64 weeks' PMA")
            elif not valid_coordinate[row]:
                failures[row] = ValueError("Invalid coordinate")
            else:
                failures[row] = DataNotFoundError("No eligible INTERGROWTH postnatal reference")
        return results, failures

    def resolve(
        self,
        *,
        indicator: Indicator | TableType | str,
        sex: Sex | str,
        age: float | None = None,
        age_definition: AgeDefinition | None = None,
        coordinate: float | None = None,
    ) -> ResolvedReference:

        kind = TableType(Indicator(indicator).value)
        _parse_sex(sex)
        if age is None or age_definition is None or age_definition.type is not AgeType.POSTMENSTRUAL:
            raise ValueError("INTERGROWTH postnatal plans require postmenstrual age for all indicators")
        pma = (
            float(age)
            * {
                AgeUnit.DAYS: 1 / 7,
                AgeUnit.WEEKS: 1,
                AgeUnit.MONTHS: 30.4375 / 7,
                AgeUnit.YEARS: 365.25 / 7,
            }[age_definition.unit]
        )
        if not math.isfinite(pma) or not 27 <= pma <= 64:
            raise DataNotFoundError("INTERGROWTH postnatal plans require 27–64 weeks' PMA")
        if kind in AGE_BASED_TYPES:
            x = pma
        else:
            if coordinate is None:
                raise ValueError("INTERGROWTH weight-for-length requires length in cm")
            x = float(coordinate)
        if not math.isfinite(x):
            raise ValueError("Invalid coordinate")
        for table in self._tables:
            if table.get_table_type() is kind and table.get_min_range() <= x <= table.get_max_range():
                return ResolvedReference(table, x)
        raise DataNotFoundError("No eligible INTERGROWTH postnatal reference")
