"""Optional reference tables and LMS calculations.

The MIT engine ships no WHO/CDC coefficient arrays. References must be
installed separately from legitimately obtained, verified source data.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from bisect import bisect_left
from collections.abc import Mapping
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from ..exceptions import DataError, DataNotFoundError, InvalidMeasurement
from ..policies import InterpolationPolicy
from ..reference_data import check_dataset_shape, parse_lms_csv, read_override_csv
from .lms import LMS
from .math import extended_bmi_z
from .sex import Sex

if TYPE_CHECKING:
    from ..provenance import ReferenceProvenance


class TableType(StrEnum):
    BodyMassIndexForAge = "bmifa"
    MidUpperArmCircumferenceForAge = "muacfa"
    TricepsSkinfoldForAge = "tsfa"
    SubscapularSkinfoldForAge = "ssfa"
    HeadCircumferenceForAge = "hcfa"
    LengthForAge = "lfa"
    HeightForAge = "hfa"
    WeightForAge = "wfa"
    WeightForHeight = "wfh"
    WeightForHeigt = "wfh"  # Historical misspelling: retained as an enum alias.
    WeightForLength = "wfl"


TYPES_ALIASES = {
    TableType.LengthForAge: TableType.HeightForAge,
    TableType.WeightForLength: TableType.WeightForHeight,
}
AGE_BASED_TYPES = frozenset(
    {
        TableType.BodyMassIndexForAge,
        TableType.MidUpperArmCircumferenceForAge,
        TableType.TricepsSkinfoldForAge,
        TableType.SubscapularSkinfoldForAge,
        TableType.HeadCircumferenceForAge,
        TableType.LengthForAge,
        TableType.HeightForAge,
        TableType.WeightForAge,
    }
)
LENGTH_BASED_TYPES = frozenset({TableType.WeightForHeight, TableType.WeightForLength})


@lru_cache(maxsize=64)
def _load_coefficients(filename: str) -> Mapping[Sex | None, Mapping[float, LMS]]:
    """Load trusted, separately installed coefficients without network access."""
    if not filename or "/" in filename or "\\" in filename or filename.startswith("."):
        raise DataError(f"Invalid reference data filename: {filename!r}")
    from ..references import read_reference

    try:
        packed = read_reference(filename, ".lmsb")
    except DataError:
        from ..references import ensure_resource

        packed = ensure_resource(filename + ".lmsb")
    if packed is None and read_reference(filename, ".csv") is None:
        from ..references import ensure_resource

        packed = ensure_resource(filename + ".lmsb")
    if packed is not None:
        from ..compiled import decode_binary

        return decode_binary(packed)
    source = read_reference(filename, ".csv")
    if source is None:
        raise DataError(
            f"Reference source {filename!r} is not installed. "
            "Install a suitable reference extension, or supply a validated "
            "local source with python -m pedgrowth.references."
        )
    try:
        from io import StringIO

        data = parse_lms_csv(StringIO(source.decode("utf-8-sig")), filename)
        return MappingProxyType({sex: MappingProxyType(values) for sex, values in data.items()})
    except (OSError, UnicodeError) as exc:
        raise DataError(f"Cannot read reference {filename!r}: {exc}") from exc


class ReferenceTable(ABC):
    """Model-independent reference contract."""

    @abstractmethod
    def get_table_type(self) -> TableType:
        """Indicator supported by this reference."""

    @abstractmethod
    def get_file_name(self) -> str:
        """Stable reference identifier."""

    def get_table_sex(self) -> Sex | None:
        return None

    def get_provenance(self) -> ReferenceProvenance | None:
        """Optional immutable source provenance for external reference tables."""
        return None

    @abstractmethod
    def get_min_range(self) -> float:
        """Lowest supported reference coordinate."""

    @abstractmethod
    def get_max_range(self) -> float:
        """Highest supported reference coordinate."""

    @abstractmethod
    def calculate_zscore(
        self,
        index_value: float,
        measurement: float,
        sex: Sex | None = None,
        interpolation: InterpolationPolicy = InterpolationPolicy.NEAREST,
    ) -> float:
        """Calculate a scalar z-score."""


class GrowthTable(ReferenceTable):
    """LMS coefficient-backed reference; legacy extension methods retained."""

    def __init__(self) -> None:
        self._table = self.get_table()
        self._set_coefficients(self._table)
        self.override_sha256: str | None = None

    def _set_coefficients(self, table: Mapping[Sex | None, Mapping[float, LMS]]) -> None:
        check_dataset_shape(
            table,
            sex_specific=self.get_col_index_sex() is not None,
            extended_bmi=self.get_col_index_sigma() is not None,
            name=self.get_file_name(),
        )
        self._table = table
        self._numpy_cache: dict[Sex | None, object] = {}
        self._indices = {sex: tuple(sorted(points)) for sex, points in table.items()}
        first = next(iter(self._indices.values()))
        self._min_range, self._max_range = first[0], first[-1]

    def use_csv_override(self, path: str | Path) -> None:
        """Replace this instance's coefficients from a validated local CSV only."""
        data, digest = read_override_csv(path)
        self._set_coefficients(data)
        self.override_sha256 = digest

    @abstractmethod
    def get_table_type(self) -> TableType:
        """Return this table's supported anthropometric indicator."""

    def get_table_sex(self) -> Sex | None:
        return None

    @abstractmethod
    def get_file_name(self) -> str:
        """Return the unique table identifier used for reference provenance."""

    def get_csv_url(self) -> str:
        raise NotImplementedError

    def get_xslx_url(self) -> str:
        raise NotImplementedError

    # Kept for extension-class compatibility. The bundled data are normalized.
    def get_col_index_sex(self) -> int | None:
        return 0

    def get_col_sex_male_value(self) -> int:
        return 1

    def get_col_index_measurement(self) -> int:
        return 1

    def get_col_index_l(self) -> int:
        return 2

    def get_col_index_m(self) -> int:
        return 3

    def get_col_index_s(self) -> int:
        return 4

    def get_col_index_sigma(self) -> int | None:
        return None

    def get_index_factor(self) -> float | None:
        return None

    def get_table(self) -> Mapping[Sex | None, Mapping[float, LMS]]:
        return _load_coefficients(self.get_file_name())

    def get_min_range(self) -> float:
        return self._min_range

    def get_max_range(self) -> float:
        return self._max_range

    def get_lms(
        self,
        index_value: float,
        sex: Sex | None = None,
        interpolation: InterpolationPolicy = InterpolationPolicy.NEAREST,
    ) -> LMS:
        selected_sex = sex if self.get_col_index_sex() is not None else None
        if selected_sex not in self._table:
            raise DataNotFoundError(f"Reference table has no data for sex {sex!r}")
        if not math.isfinite(float(index_value)):
            raise DataNotFoundError(f"Invalid index: {index_value!r}")
        indices = self._indices[selected_sex]
        if index_value < indices[0] or index_value > indices[-1]:
            raise DataNotFoundError(f"Index {index_value} outside [{indices[0]}, {indices[-1]}]")
        position = bisect_left(indices, index_value)
        if position == len(indices):
            nearest = indices[-1]
        elif position == 0:
            nearest = indices[0]
        else:
            before, after = indices[position - 1], indices[position]
            nearest = before if (index_value - before) <= (after - index_value) else after
        if interpolation is InterpolationPolicy.NEAREST or index_value == nearest:
            return self._table[selected_sex][nearest]
        if interpolation is not InterpolationPolicy.LINEAR:
            raise ValueError(f"Unsupported interpolation policy: {interpolation!r}")
        if position == 0 or position >= len(indices):
            return self._table[selected_sex][nearest]
        left, right = indices[position - 1], indices[position]
        low, high = self._table[selected_sex][left], self._table[selected_sex][right]
        fraction = (index_value - left) / (right - left)

        def blend(a: float, b: float) -> float:
            return a + fraction * (b - a)

        sigma: float | None = None
        p95: float | None = None
        if low.sigma is not None and high.sigma is not None:
            if sex is None:
                raise DataError("CDC extended BMI requires sex")
            age_years = index_value / 12
            sigma = (
                0.3728 + 0.5196 * age_years - 0.0091 * age_years**2
                if sex is Sex.Male
                else 0.8334 + 0.3712 * age_years - 0.0011 * age_years**2
            )
        if low.p95 is not None and high.p95 is not None:
            p95 = blend(low.p95, high.p95)
        return LMS(blend(low.l, high.l), blend(low.m, high.m), blend(low.s, high.s), sigma, p95)

    def calculate_zscore(
        self,
        index_value: float,
        measurement: float,
        sex: Sex | None = None,
        interpolation: InterpolationPolicy = InterpolationPolicy.NEAREST,
    ) -> float:
        if not math.isfinite(measurement) or measurement <= 0:
            raise InvalidMeasurement(f"Measurement must be finite and > 0: {measurement!r}")
        lms = self.get_lms(index_value, sex, interpolation=interpolation)
        # Test the CDC extended-BMI threshold before LMS evaluation: extreme
        # valid BMIs need not lie in the numerical domain of the raw LMS power.
        if self.get_col_index_sigma() is not None:
            if lms.sigma is None:
                raise DataError("Extended BMI table is missing sigma")
            if lms.p95 is None:
                raise DataError("CDC extended BMI requires the published P95 threshold")
            if measurement > lms.p95:
                t = (measurement - lms.p95) / lms.sigma
                if not math.isfinite(t):
                    raise InvalidMeasurement("Extended BMI exceeds representable numeric range")
                return extended_bmi_z(t)

        ratio = measurement / lms.m
        if not math.isfinite(ratio) or ratio <= 0:
            raise InvalidMeasurement("Measurement is outside representable LMS numeric range")
        try:
            if lms.l == 0:
                zscore = math.log(ratio) / lms.s
            else:
                zscore = (ratio**lms.l - 1) / (lms.l * lms.s)
        except (OverflowError, ZeroDivisionError) as exc:
            raise InvalidMeasurement("Measurement exceeds representable LMS range") from exc
        if not math.isfinite(zscore):
            raise InvalidMeasurement("Nonfinite LMS z-score for the supplied measurement")
        return zscore

    def calculate_sd(self, lms: LMS, position: float) -> float:
        if lms.l == 0:
            return lms.m * math.exp(lms.s * position)
        base = 1 + lms.l * lms.s * position
        if base <= 0:
            raise DataError("WHO standard-deviation point is outside the LMS domain")
        return float(lms.m * base ** (1 / lms.l))


LMSTable = GrowthTable  # Explicit LMS model alias; legacy subclass API remains valid.
