"""Optional NumPy execution of typed table and plan calculations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .architecture import AgeDefinition, Indicator
    from .pygrowup import GrowthChartsCalculator


def calculate_numpy(
    calculator: GrowthChartsCalculator,
    *,
    indicator: Indicator | str,
    measurements: object,
    sexes: object,
    ages: object | None = None,
    age_definition: AgeDefinition | None = None,
    coordinates: object | None = None,
    errors: str = "raise",
) -> tuple[object, object]:
    """Return z-scores and reference IDs, preserving row order.

    Built-in plan reference-selection policies produce vectorized eligibility
    masks; resolved rows are grouped by table for compiled LMS evaluation.
    Custom scalar-only plans remain supported as a compatibility fallback.
    """
    import numpy as np

    from .batch import _evaluate
    from .exceptions import PyGrowUpError
    from .pygrowup import _parse_sex
    from .tables import GrowthTable, ReferenceTable, Sex

    if errors not in ("raise", "coerce"):
        raise ValueError("errors must be raise or coerce")
    raw_values = np.asarray(measurements)
    if raw_values.ndim != 1:
        raise ValueError("measurements must be one-dimensional")
    n = len(raw_values)

    def broadcast(data: object | None, name: str) -> Any:
        if data is None:
            return None
        array = np.asarray(data)
        if array.ndim == 0:
            return np.repeat(array, n)
        if array.ndim != 1 or len(array) != n:
            raise ValueError(f"{name} must be scalar or a matching one-dimensional array")
        return array

    def numeric(data: object | None, name: str) -> Any:
        array = broadcast(data, name)
        if array is None:
            return None
        try:
            return np.asarray(array, dtype=float)
        except (TypeError, ValueError, OverflowError):
            if errors == "raise":
                raise ValueError(f"{name} must contain numeric values") from None
            # Only the exceptional mixed-type case needs per-item conversion;
            # numeric arrays continue to use the fast vectorized path.
            cleaned = np.full(n, np.nan, dtype=float)
            for position, value in enumerate(array):
                try:
                    if isinstance(value, (bool, np.bool_)):
                        continue
                    cleaned[position] = float(value)
                except (TypeError, ValueError, OverflowError):
                    pass
            return cleaned

    values = numeric(raw_values, "measurements")
    sex_array = broadcast(sexes, "sexes")
    if sex_array is None:
        raise ValueError("sexes must be provided")
    age_array = numeric(ages, "ages")
    coordinate_array = numeric(coordinates, "coordinates")
    result = np.full(n, np.nan, dtype=float)
    ids = np.full(n, "", dtype=object)
    groups: dict[tuple[ReferenceTable, Sex], list[tuple[int, float, float]]] = {}
    resolved_batch = None
    plan_batch_resolver = getattr(calculator.plan, "resolve_numpy", None)
    if callable(plan_batch_resolver):
        resolved_batch, failures = plan_batch_resolver(
            indicator=indicator,
            sexes=sex_array,
            ages=age_array,
            age_definition=age_definition,
            coordinates=coordinate_array,
        )
        if errors == "raise":
            for failure in failures:
                if failure is not None:
                    raise failure
    for i in range(n):
        try:
            sex = _parse_sex(str(sex_array[i]))
            measure = float(values[i])
            if not np.isfinite(measure) or measure <= 0:
                raise ValueError("Measurement must be finite and positive")
            if resolved_batch is not None:
                resolved = resolved_batch[i]
                if resolved is None:
                    continue
            else:
                resolved = calculator.resolve(
                    indicator=indicator,
                    sex=sex,
                    age=float(age_array[i]) if age_array is not None else None,
                    age_definition=age_definition,
                    coordinate=float(coordinate_array[i]) if coordinate_array is not None else None,
                )
            if measure + resolved.measurement_offset <= 0:
                raise ValueError("Position-adjusted measurement must be positive")
            groups.setdefault((resolved.table, sex), []).append(
                (i, resolved.coordinate, resolved.measurement_offset)
            )
            ids[i] = resolved.reference_id
        except (ValueError, LookupError, PyGrowUpError):
            if errors == "raise":
                raise
    for (table, sex), rows in groups.items():
        positions = np.asarray([row[0] for row in rows], dtype=int)
        ix = np.asarray([row[1] for row in rows], dtype=float)
        adjusted_values = values[positions] + np.asarray([row[2] for row in rows])
        try:
            if isinstance(table, GrowthTable):
                z = _evaluate(table, ix, adjusted_values, sex, calculator.interpolation)
            else:
                # A custom ReferenceTable need only implement the scalar contract;
                # specialized non-LMS models can later add an optional batch adapter.
                z = np.asarray(
                    [
                        table.calculate_zscore(
                            float(x), float(y), sex, interpolation=calculator.interpolation
                        )
                        for x, y in zip(ix, adjusted_values, strict=True)
                    ],
                    dtype=float,
                )
            result[positions] = z
        except (ValueError, LookupError, PyGrowUpError):
            if errors == "raise":
                raise
            for i, x, measurement_offset in rows:
                try:
                    result[i] = table.calculate_zscore(
                        x,
                        float(values[i]) + measurement_offset,
                        sex,
                        interpolation=calculator.interpolation,
                    )
                except (ValueError, LookupError, PyGrowUpError):
                    ids[i] = ""
    return result, ids
