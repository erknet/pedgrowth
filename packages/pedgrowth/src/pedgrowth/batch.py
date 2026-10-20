"""Optional NumPy/SciPy bulk evaluation of anthropometric LMS references.

NumPy implements searchsorted and arithmetic in compiled C; SciPy supplies
numerically stable normal CDF/inverse CDF for CDC extended BMI. These packages
are imported only when the user explicitly calls the vectorized API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .exceptions import DataError, DataNotFoundError, InvalidMeasurement
from .policies import InterpolationPolicy
from .tables.math import extended_bmi_z
from .tables.sex import Sex
from .tables.table import AGE_BASED_TYPES, TYPES_ALIASES, LMSTable, TableType

FloatArray = NDArray[np.float64]


def _norm_cdf(values: FloatArray) -> FloatArray:
    """Use SciPy when available, otherwise a stdlib-only NumPy-compatible fallback."""
    try:
        from scipy.special import ndtr
    except ImportError:
        normal = NormalDist()
        return np.fromiter((normal.cdf(float(x)) for x in values), dtype=np.float64, count=len(values))
    return np.asarray(ndtr(values), dtype=np.float64)


def _norm_ppf(values: FloatArray) -> FloatArray:
    try:
        from scipy.special import ndtri
    except ImportError:
        normal = NormalDist()
        return np.fromiter((normal.inv_cdf(float(x)) for x in values), dtype=np.float64, count=len(values))
    return np.asarray(ndtri(values), dtype=np.float64)


@dataclass(frozen=True, slots=True)
class _Prepared:
    keys: FloatArray
    l: FloatArray
    m: FloatArray
    s: FloatArray
    sigma: FloatArray
    p95: FloatArray


def _prepare(table: LMSTable, sex: Sex | None) -> _Prepared:
    existing = table._numpy_cache.get(sex)
    if isinstance(existing, _Prepared):
        return existing
    rows = table._table[sex]
    keys = np.asarray(table._indices[sex], dtype=np.float64)
    observations = [rows[float(index)] for index in keys]

    def values(field: str) -> FloatArray:
        return np.fromiter(
            (getattr(item, field) if getattr(item, field) is not None else math.nan for item in observations),
            dtype=np.float64,
        )

    prepared = _Prepared(
        keys,
        values("l"),
        values("m"),
        values("s"),
        values("sigma"),
        values("p95"),
    )
    for arr in (
        prepared.keys,
        prepared.l,
        prepared.m,
        prepared.s,
        prepared.sigma,
        prepared.p95,
    ):
        arr.setflags(write=False)
    table._numpy_cache[sex] = prepared
    return prepared


def _vector(values: ArrayLike, name: str, *, allow_zero: bool) -> FloatArray:
    try:
        a = np.asarray(values)
        if a.dtype.kind not in "iuf":
            raise ValueError("Only real numeric arrays are accepted")
        result = np.asarray(a, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InvalidMeasurement(f"Invalid {name}: {exc}") from exc
    if result.ndim != 1:
        raise InvalidMeasurement(f"{name} must be one-dimensional")
    if not bool(np.all(np.isfinite(result))):
        raise InvalidMeasurement(f"{name} contains non-finite values")
    if bool(np.any(result < 0 if allow_zero else result <= 0)):
        raise InvalidMeasurement(f"{name} must contain nonnegative or positive values")
    return result


def _sd(l: FloatArray, m: FloatArray, s: FloatArray, level: int) -> FloatArray:
    base = 1.0 + l * s * level
    result = np.empty_like(l)
    is_log = l == 0.0
    result[is_log] = m[is_log] * np.exp(s[is_log] * level)
    ok = ~is_log
    if bool(np.any(base[ok] <= 0)):
        raise InvalidMeasurement("WHO SD reference outside LMS domain")
    result[ok] = m[ok] * np.power(base[ok], 1.0 / l[ok])
    return result


def _evaluate(
    table: LMSTable,
    indices: FloatArray,
    measures: FloatArray,
    sex: Sex,
    interpolation: InterpolationPolicy,
) -> FloatArray:
    selected = sex if table.get_col_index_sex() is not None else None
    prepared = _prepare(table, selected)
    keys = prepared.keys
    insertion = np.searchsorted(keys, indices)
    right = np.clip(insertion, 0, len(keys) - 1)
    left = np.clip(insertion - 1, 0, len(keys) - 1)
    nearest = np.where(indices - keys[left] <= keys[right] - indices, left, right)

    def resolve(values: FloatArray) -> FloatArray:
        if interpolation is InterpolationPolicy.NEAREST:
            return values[nearest]
        span = keys[right] - keys[left]
        fraction = np.divide(
            indices - keys[left],
            span,
            out=np.zeros_like(indices),
            where=span > 0,
        )
        return values[left] + fraction * (values[right] - values[left])

    l = resolve(prepared.l)
    m = resolve(prepared.m)
    s = resolve(prepared.s)
    log_case = l == 0.0
    z = np.empty_like(measures)
    with np.errstate(divide="ignore", over="ignore", under="ignore", invalid="ignore"):
        z[log_case] = np.log(measures[log_case] / m[log_case]) / s[log_case]
        z[~log_case] = (np.power(measures[~log_case] / m[~log_case], l[~log_case]) - 1.0) / (
            l[~log_case] * s[~log_case]
        )

    if table.get_col_index_sigma() is not None:
        sigma = resolve(prepared.sigma)
        if interpolation is InterpolationPolicy.LINEAR:
            age_years = indices / 12.0
            polynomial = (
                0.3728 + 0.5196 * age_years - 0.0091 * age_years**2
                if sex is Sex.Male
                else 0.8334 + 0.3712 * age_years - 0.0011 * age_years**2
            )
            exact = keys[right] == indices
            sigma = np.where(exact, sigma, polynomial)
        if not bool(np.all(np.isfinite(sigma))):
            raise InvalidMeasurement("Extended BMI reference is missing sigma")
        bmi95 = resolve(prepared.p95)
        if not bool(np.all(np.isfinite(bmi95))):
            raise InvalidMeasurement("Extended BMI reference is missing published P95")
        mask = measures > bmi95
        if bool(np.any(mask)):
            standardized = (measures[mask] - bmi95[mask]) / sigma[mask]
            # NormalDist/SciPy cdf loses the right tail beyond ~8 SD.
            stable = standardized >= 6
            calculated = np.empty_like(standardized)
            if bool(np.any(~stable)):
                percentile = 0.90 + 0.10 * _norm_cdf(standardized[~stable])
                calculated[~stable] = _norm_ppf(percentile)
            if bool(np.any(stable)):
                calculated[stable] = np.fromiter(
                    (extended_bmi_z(float(v)) for v in standardized[stable]),
                    dtype=np.float64,
                    count=int(np.count_nonzero(stable)),
                )
            z[mask] = calculated
    elif bool(getattr(table, "use_sd_tails", False)):
        higher = z > 3
        lower = z < -3
        if bool(np.any(higher)):
            sd3 = _sd(l[higher], m[higher], s[higher], 3)
            sd2 = _sd(l[higher], m[higher], s[higher], 2)
            z[higher] = 3 + (measures[higher] - sd3) / (sd3 - sd2)
        if bool(np.any(lower)):
            sd3 = _sd(l[lower], m[lower], s[lower], -3)
            sd2 = _sd(l[lower], m[lower], s[lower], -2)
            z[lower] = -3 + (measures[lower] - sd3) / (sd2 - sd3)
    if not bool(np.all(np.isfinite(z))):
        raise InvalidMeasurement("Nonfinite LMS or tail z-score for the supplied measurement")
    return z


def calculate_many(
    calculator: object,
    indicator: TableType,
    measurements: ArrayLike,
    index_values: ArrayLike,
    sex: Sex,
    *,
    is_recumbent_height: bool = False,
) -> FloatArray:
    """Evaluate a single indicator/sex over arbitrary one-dimensional NumPy arrays.

    Uses exact same nearest-reference and table precedence rules as the
    scalar calculator, and applies the 0.7 cm height/length correction.
    Invalid/missing measurements are rejected; partial batch results are
    never returned on an error.
    """
    # Broadcast a scalar input against a 1-D numeric NumPy array.
    # Explicit batch evaluation of two scalars returns a 1-element array.
    raw_measures = np.asarray(measurements)
    raw_indices = np.asarray(index_values)
    if raw_measures.ndim == 0:
        if raw_indices.ndim > 1:
            raise InvalidMeasurement("Indices must be one-dimensional")
        raw_measures = np.full(raw_indices.shape if raw_indices.ndim else (1,), raw_measures.item())
    if raw_indices.ndim == 0:
        if raw_measures.ndim > 1:
            raise InvalidMeasurement("Measurements must be one-dimensional")
        raw_indices = np.full(raw_measures.shape, raw_indices.item())
    measures = _vector(raw_measures, "measurements", allow_zero=False)
    ix = _vector(raw_indices, "indices", allow_zero=indicator in AGE_BASED_TYPES)
    if len(measures) != len(ix):
        raise InvalidMeasurement("Measurements and indices must have the same length")
    if len(ix) == 0:
        return np.empty(0, dtype=np.float64)

    # The public GrowthChartsCalculator owns reference selection and data overrides.
    from .pygrowup import GrowthChartsCalculator

    if not isinstance(calculator, GrowthChartsCalculator):
        raise TypeError("calculator must be a GrowthChartsCalculator")
    result = np.empty_like(measures)
    unresolved = np.ones(len(measures), dtype=np.bool_)
    missing_reference: Exception | None = None
    indicator_order = (indicator, TYPES_ALIASES[indicator]) if indicator in TYPES_ALIASES else (indicator,)
    for table_type in indicator_order:
        for prototype in calculator._by_type.get(table_type, ()):
            if prototype.get_table_sex() not in (None, sex) or not bool(np.any(unresolved)):
                continue
            try:
                table = calculator._load_matching_table(prototype)
            except DataError as exc:
                missing_reference = exc
                import warnings

                warnings.warn(
                    f"Reference {prototype.get_file_name()} unavailable: {exc}; retry on next access",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            usable = unresolved & (ix >= table.get_min_range()) & (ix <= table.get_max_range())
            if not bool(np.any(usable)):
                continue
            inputs = ix[usable].copy()
            outputs = measures[usable].copy()
            if calculator.adjust_height_data:
                if table_type == TableType.HeightForAge and is_recumbent_height:
                    outputs -= 0.7
                elif table_type == TableType.LengthForAge and not is_recumbent_height:
                    outputs += 0.7
                elif table_type == TableType.WeightForHeight and is_recumbent_height:
                    inputs -= 0.7
                elif table_type == TableType.WeightForLength and not is_recumbent_height:
                    inputs += 0.7
            if bool(np.any(outputs <= 0)):
                raise InvalidMeasurement("Adjusted measurement is not positive")
            if bool(np.any((inputs < table.get_min_range()) | (inputs > table.get_max_range()))):
                raise DataNotFoundError("Adjusted indices fall outside the selected reference")
            result[usable] = _evaluate(table, inputs, outputs, sex, calculator.interpolation)
            unresolved[usable] = False
    if bool(np.any(unresolved)):
        if missing_reference is not None:
            raise missing_reference
        raise DataNotFoundError(
            f"No reference for {indicator.value}, sex={sex.value}, index={float(ix[unresolved][0])}"
        ) from None
    return result
