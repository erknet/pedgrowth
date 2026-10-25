"""WHO-specific age ranges and standing/recumbent selection adjustments.

These provider rules never ship with the generic pedgrowth engine.
"""

from __future__ import annotations

from pedgrowth.registry import ReferenceBatchCandidate, ReferenceCandidate
from pedgrowth.tables import TableType
from pedgrowth.tables.table import ReferenceTable


def candidates(kind: TableType, age_months: float | None, mode: str | None) -> tuple[ReferenceCandidate, ...]:
    clinical = mode == "clinical"
    targets: tuple[TableType, ...]
    if clinical and kind in (TableType.LengthForAge, TableType.HeightForAge):
        targets = (TableType.LengthForAge,)
    elif clinical and kind in (TableType.WeightForLength, TableType.WeightForHeight):
        targets = (TableType.WeightForLength,)
    elif kind is TableType.WeightForLength:
        targets = (TableType.WeightForLength, TableType.WeightForHeight)
    elif kind is TableType.WeightForHeight:
        targets = (TableType.WeightForHeight, TableType.WeightForLength)
    elif kind is TableType.HeightForAge:
        targets = (TableType.HeightForAge, TableType.LengthForAge)
    elif kind is TableType.LengthForAge:
        targets = (TableType.LengthForAge, TableType.HeightForAge)
    else:
        targets = (kind,)
    matches = []
    for target in targets:
        shift = (
            -0.7
            if kind is TableType.WeightForLength and target is TableType.WeightForHeight
            else 0.7
            if kind is TableType.WeightForHeight and target is TableType.WeightForLength
            else 0.0
        )
        measurement = (
            0.7
            if kind is TableType.HeightForAge
            and target is TableType.LengthForAge
            and age_months is not None
            and age_months < 24
            else -0.7
            if kind is TableType.LengthForAge
            and (target is TableType.HeightForAge or age_months is not None and age_months >= 24)
            else 0.0
        )
        matches.append(ReferenceCandidate(target, shift, measurement))
    return tuple(matches)


def batch_candidates(
    kind: TableType, age_months: object | None, mode: str | None
) -> tuple[ReferenceBatchCandidate, ...]:
    import numpy as np

    clinical = mode == "clinical"
    targets: tuple[TableType, ...]
    if clinical and kind in (TableType.LengthForAge, TableType.HeightForAge):
        targets = (TableType.LengthForAge,)
    elif clinical and kind in (TableType.WeightForLength, TableType.WeightForHeight):
        targets = (TableType.WeightForLength,)
    elif kind in (TableType.WeightForLength, TableType.WeightForHeight):
        targets = (
            kind,
            TableType.WeightForHeight if kind is TableType.WeightForLength else TableType.WeightForLength,
        )
    elif kind in (TableType.LengthForAge, TableType.HeightForAge):
        targets = (kind, TableType.HeightForAge if kind is TableType.LengthForAge else TableType.LengthForAge)
    else:
        targets = (kind,)
    ages = np.asarray(age_months, dtype=float) if age_months is not None else None
    result = []
    for target in targets:
        coordinate = (
            -0.7
            if kind is TableType.WeightForLength and target is TableType.WeightForHeight
            else 0.7
            if kind is TableType.WeightForHeight and target is TableType.WeightForLength
            else 0.0
        )
        if kind is TableType.HeightForAge and target is TableType.LengthForAge:
            offset = np.where(ages < 24, 0.7, 0.0) if ages is not None else 0.0
        elif kind is TableType.LengthForAge:
            offset = (
                -0.7
                if target is TableType.HeightForAge
                else np.where(ages >= 24, -0.7, 0.0)
                if ages is not None
                else 0.0
            )
        else:
            offset = 0.0
        result.append(ReferenceBatchCandidate(target, coordinate, offset))
    return tuple(result)


def batch_accept(
    table: ReferenceTable, kind: TableType, age_months: object | None, target: TableType, mode: str | None
) -> object:
    import numpy as np

    if kind in (TableType.WeightForLength, TableType.WeightForHeight) and age_months is not None:
        ages = np.asarray(age_months, dtype=float)
        return ages < 24 if target is TableType.WeightForLength else ages >= 24
    return True


def accept(
    table: ReferenceTable,
    kind: TableType,
    age_months: float | None,
    target: TableType,
    mode: str | None,
) -> bool:
    if kind in (TableType.WeightForLength, TableType.WeightForHeight) and age_months is not None:
        return (target is TableType.WeightForLength) == (age_months < 24)
    return True
