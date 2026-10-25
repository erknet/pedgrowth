"""Optional vectorized Pandas adapter backed by NumPy batch evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import DataNotFoundError, InvalidMeasurement
from .pygrowup import GrowthChartsCalculator

if TYPE_CHECKING:
    import pandas as pd  # type: ignore[import-untyped]

    from .architecture import AgeDefinition


def calculate_dataframe(
    frame: pd.DataFrame,
    calculator: GrowthChartsCalculator,
    *,
    indicator: str,
    measurement: str,
    index: str,
    sex: str,
    output: str = "zscore",
    errors: str = "raise",
) -> pd.DataFrame:
    """Return a copy with vectorized z-scores, grouped by sex.

    NumPy and Pandas are optional dependencies. ``errors='coerce'`` marks
    invalid rows as NaN; vectorized groups are evaluated together where valid.
    """
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise ImportError("Install the [pandas] extra (which includes NumPy)") from exc

    if errors not in ("raise", "coerce"):
        raise ValueError("errors must be raise or coerce")
    if not output or output in frame.columns:
        raise ValueError("output must be a new, nonempty column name")
    missing = {measurement, index, sex} - set(frame.columns)
    if missing:
        raise KeyError(f"Missing input columns: {sorted(missing)}")
    if not frame.columns.is_unique:
        raise ValueError("Input DataFrame columns must be unique")

    from .tables import AGE_BASED_TYPES, TableType

    kind = next((t for t in TableType if t.value == indicator), None)
    if kind is None:
        raise ValueError(f"Unknown indicator: {indicator!r}")
    measure = pd.to_numeric(frame[measurement], errors="coerce").to_numpy(dtype="float64")
    coordinates = pd.to_numeric(frame[index], errors="coerce").to_numpy(dtype="float64")
    genders = frame[sex].astype("string").str.strip().str.upper().to_numpy(dtype=str, na_value="")
    genders = np.where(
        np.isin(genders, ["M", "MALE"]), "M", np.where(np.isin(genders, ["F", "FEMALE"]), "F", "")
    )
    valid = np.isfinite(measure) & np.isfinite(coordinates) & (measure > 0)
    valid &= coordinates >= 0 if kind in AGE_BASED_TYPES else coordinates > 0
    valid &= genders != ""
    if errors == "raise" and not bool(np.all(valid)):
        raise ValueError(f"Invalid input at row position {int(np.flatnonzero(~valid)[0])}")
    results = np.full(len(frame), np.nan, dtype="float64")
    for gender in ("M", "F"):
        selected = np.flatnonzero(valid & (genders == gender))
        if not len(selected):
            continue
        try:
            results[selected] = calculator.zscores_numpy(
                kind, measure[selected], coordinates[selected], gender
            )
        except (ValueError, LookupError, DataNotFoundError, InvalidMeasurement):
            if errors == "raise":
                raise
            # Fallback only for mixed-validity batches; keep the normal path vectorized.
            for position in selected:
                try:
                    results[position] = (
                        calculator.zscore_for_measurement(
                            kind, float(measure[position]), gender, float(coordinates[position])
                        )
                        or 0.0
                    )
                except (ValueError, LookupError, DataNotFoundError, InvalidMeasurement):
                    pass
    result = frame.copy()
    result[output] = pd.Series(results, index=frame.index, dtype="float64")
    return result


def calculate_typed_dataframe(
    frame: pd.DataFrame,
    calculator: GrowthChartsCalculator,
    *,
    indicator: str,
    measurement: str,
    sex: str,
    age: str | None = None,
    age_definition: AgeDefinition | None = None,
    coordinate: str | None = None,
    output: str = "zscore",
    reference_output: str | None = "reference_id",
    errors: str = "raise",
) -> pd.DataFrame:
    """Typed plan/table adapter; Pandas is an optional import."""
    import numpy as np
    import pandas as pd

    names = [measurement, sex] + ([age] if age else []) + ([coordinate] if coordinate else [])
    outputs = [output] + ([reference_output] if reference_output else [])
    if not frame.columns.is_unique or len(set(outputs)) != len(outputs):
        raise ValueError("Column names must be unique")
    if any(name not in frame.columns for name in names):
        raise KeyError("Missing input column")
    if any(name in frame.columns for name in outputs):
        raise ValueError("Output column already exists")
    values = pd.to_numeric(frame[measurement], errors="coerce").to_numpy(dtype=float)
    ages = pd.to_numeric(frame[age], errors="coerce").to_numpy(dtype=float) if age else None
    coords = pd.to_numeric(frame[coordinate], errors="coerce").to_numpy(dtype=float) if coordinate else None
    sexes = frame[sex].astype("string").fillna("").to_numpy(dtype=str)
    scores, refs = calculator.calculate_numpy(
        indicator=indicator,
        measurements=values,
        sexes=sexes,
        ages=ages,
        age_definition=age_definition,
        coordinates=coords,
        errors=errors,
    )
    result = frame.copy()
    result[output] = pd.Series(np.asarray(scores, dtype=float), index=frame.index)
    if reference_output:
        result[reference_output] = pd.Series(refs, index=frame.index, dtype="string")
    return result
