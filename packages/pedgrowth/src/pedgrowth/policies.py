"""Explicit reference and age-index resolution policies.

The defaults preserve the original library's table precedence and nearest-row
lookup. Nondefault interpolation is opt-in and documented separately.
"""

from __future__ import annotations

from enum import StrEnum


class ReferenceStandard(StrEnum):
    WHO = "who"
    CDC = "cdc"
    WHO_THEN_CDC = "who_then_cdc"
    CDC_THEN_WHO = "cdc_then_who"


class InterpolationPolicy(StrEnum):
    NEAREST = "nearest"
    LINEAR = "linear"


class MeasurementPosition(StrEnum):
    RECUMBENT = "recumbent"
    STANDING = "standing"
