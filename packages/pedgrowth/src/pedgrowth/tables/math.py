"""Numerical functions for LMS and normally distributed z-scores."""

from __future__ import annotations

import math
from statistics import NormalDist

from .lms import LMS

normal_dist = NormalDist()


def z_to_percentile(z: float) -> float:
    """Convert a z-score to a cumulative proportion between 0 and 1."""
    return normal_dist.cdf(float(z))


def percentile_to_z(percentile: float) -> float:
    """Convert a cumulative proportion between 0 and 1 to a z-score."""
    return normal_dist.inv_cdf(percentile)


def calculate_value_by_percentile(percentile: float, lms: LMS) -> float:
    """Calculate the measurement for a cumulative percentile (e.g. 0.95)."""
    z = percentile_to_z(percentile)
    if lms.l == 0:
        return lms.m * math.exp(lms.s * z)
    base = 1 + lms.l * lms.s * z
    if base <= 0:
        raise ValueError("The requested percentile is outside the LMS domain")
    return float(lms.m * base ** (1 / lms.l))


def extended_bmi_z(standardized_excess: float) -> float:
    """Numerically stable CDC 2022 extended BMI z-score above published P95.

    The CDC formula is Phi^{-1}(0.9 + 0.1 Phi(excess)). For large excess
    this rounds to Phi^{-1}(1) and loses precision; solve the equivalent
    survival-probability equation without subtracting from 1.
    """
    t = float(standardized_excess)
    if not math.isfinite(t):
        raise ValueError("Extended BMI standardized excess must be finite")
    if t < 6:
        return percentile_to_z(0.90 + 0.10 * z_to_percentile(t))
    # For t this large, the normal-survival correction is below half a
    # float64 ULP. Returning t avoids overflowing the squared exponent.
    if t >= 1e10:
        return t

    def log_survival(x: float) -> float:
        if x < 25:
            return math.log(0.5 * math.erfc(x / math.sqrt(2)))
        inverse_sq = 1 / (x * x)
        correction = 1 - inverse_sq + 3 * inverse_sq**2 - 15 * inverse_sq**3 + 105 * inverse_sq**4
        return -0.5 * x**2 - math.log(x) - 0.5 * math.log(2 * math.pi) + math.log(correction)

    log_target = math.log(0.1) + log_survival(t)
    lo = t
    hi = t + 5
    for _ in range(65):
        midpoint = lo + 0.5 * (hi - lo)
        if log_survival(midpoint) > log_target:
            lo = midpoint
        else:
            hi = midpoint
    return lo + 0.5 * (hi - lo)
