"""WHO growth-reference coordinate conversion and SD-tail adjustment."""

from __future__ import annotations

import math

from pedgrowth.exceptions import InvalidMeasurement
from pedgrowth.policies import InterpolationPolicy
from pedgrowth.tables import AGE_BASED_TYPES, Sex
from pedgrowth.tables.table import LMSTable


class WhoGrowthTable(LMSTable):
    """WHO 2006 age tables use days; normalized LMS indices use months."""

    def get_col_index_sex(self) -> None:
        return None

    def get_col_index_measurement(self) -> int:
        return 0

    def get_col_index_l(self) -> int:
        return 1

    def get_col_index_m(self) -> int:
        return 2

    def get_col_index_s(self) -> int:
        return 3

    def get_index_factor(self) -> float | None:
        return 1 / 30.4375 if self.get_table_type() in AGE_BASED_TYPES else None


class WhoRightSkewedGrowthTable(WhoGrowthTable):
    use_sd_tails = True
    """Apply WHO linear extrapolation beyond ±3 SD for skewed indicators."""

    def calculate_zscore(
        self,
        index_value: float,
        measurement: float,
        sex: Sex | None = None,
        interpolation: InterpolationPolicy = InterpolationPolicy.NEAREST,
    ) -> float:
        # Check the WHO -3/+3 SD physical thresholds before evaluating LMS.
        # This avoids overflowing the raw power expression on tiny positive
        # measurements that are correctly evaluated by linear SD tails.
        if not math.isfinite(measurement) or measurement <= 0:
            raise InvalidMeasurement("Measurement must be finite and positive")
        lms = self.get_lms(index_value, sex, interpolation=interpolation)
        minus3 = self.calculate_sd(lms, -3)
        plus3 = self.calculate_sd(lms, 3)
        if measurement < minus3:
            minus2 = self.calculate_sd(lms, -2)
            return -3 + (measurement - minus3) / (minus2 - minus3)
        if measurement > plus3:
            plus2 = self.calculate_sd(lms, 2)
            return 3 + (measurement - plus3) / (plus3 - plus2)
        return super().calculate_zscore(index_value, measurement, sex, interpolation=interpolation)
