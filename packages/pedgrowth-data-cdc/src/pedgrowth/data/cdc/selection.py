"""CDC selection conventions, including the clinical 24-month boundary."""

from __future__ import annotations

from pedgrowth.registry import ReferenceBatchCandidate, ReferenceCandidate
from pedgrowth.tables import TableType
from pedgrowth.tables.table import AGE_BASED_TYPES, TYPES_ALIASES, ReferenceTable


def candidates(kind: TableType, age_months: float | None, mode: str | None) -> tuple[ReferenceCandidate, ...]:
    if mode == "clinical":
        if kind in (TableType.LengthForAge, TableType.HeightForAge):
            return (
                ReferenceCandidate(
                    TableType.HeightForAge,
                    measurement_offset=(-0.7 if kind is TableType.LengthForAge else 0.0),
                ),
            )
        if kind in (TableType.WeightForLength, TableType.WeightForHeight):
            return (
                ReferenceCandidate(
                    TableType.WeightForHeight,
                    coordinate_offset=(-0.7 if kind is TableType.WeightForLength else 0.0),
                ),
            )
    alias = TYPES_ALIASES.get(kind)
    return (
        (ReferenceCandidate(kind), ReferenceCandidate(alias))
        if alias is not None
        else (ReferenceCandidate(kind),)
    )


def batch_candidates(
    kind: TableType, age_months: object | None, mode: str | None
) -> tuple[ReferenceBatchCandidate, ...]:
    if mode == "clinical":
        if kind in (TableType.LengthForAge, TableType.HeightForAge):
            return (
                ReferenceBatchCandidate(
                    TableType.HeightForAge, measurement_offset=-0.7 if kind is TableType.LengthForAge else 0.0
                ),
            )
        if kind in (TableType.WeightForLength, TableType.WeightForHeight):
            return (
                ReferenceBatchCandidate(
                    TableType.WeightForHeight,
                    coordinate_offset=-0.7 if kind is TableType.WeightForLength else 0.0,
                ),
            )
    alias = TYPES_ALIASES.get(kind)
    return (
        (ReferenceBatchCandidate(kind), ReferenceBatchCandidate(alias))
        if alias is not None
        else (ReferenceBatchCandidate(kind),)
    )


def batch_accept(
    table: ReferenceTable, kind: TableType, age_months: object | None, target: TableType, mode: str | None
) -> object:
    import numpy as np

    if (
        mode == "clinical"
        and kind in AGE_BASED_TYPES
        and age_months is not None
        and table.get_file_name().endswith("_0_36")
    ):
        return np.asarray(age_months, dtype=float) < 24
    return True


def accept(
    table: ReferenceTable,
    kind: TableType,
    age_months: float | None,
    target: TableType,
    mode: str | None,
) -> bool:
    return not (
        mode == "clinical"
        and kind in AGE_BASED_TYPES
        and age_months is not None
        and age_months >= 24
        and table.get_file_name().endswith("_0_36")
    )
