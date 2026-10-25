"""INTERGROWTH-21st preterm anthropometry using published regression equations.

The postnatal standard uses postmenstrual age in weeks; very-preterm
size at birth uses gestational age in days. These are separate from WHO/CDC.
"""

from __future__ import annotations

import math
from enum import StrEnum


class IntergrowthReference(StrEnum):
    PRETERM_POSTNATAL = "preterm_postnatal"
    VERY_PRETERM_BIRTH = "very_preterm_birth"


class IntergrowthIndicator(StrEnum):
    WEIGHT = "weight"
    LENGTH = "length"
    HEAD_CIRCUMFERENCE = "head_circumference"
    WEIGHT_FOR_LENGTH = "weight_for_length"


class IntergrowthCalculator:
    """Calculate preterm INTERGROWTH-21st z-scores from reference equations.

    Measurements: weight in kg, length/head circumference in cm.
    Age: postmenstrual weeks for PRETERM_POSTNATAL (27–64); gestational
    days for VERY_PRETERM_BIRTH (168–230). No extrapolation is permitted.
    """

    def __init__(self, reference: IntergrowthReference | str) -> None:
        from .data import read_intergrowth_coefficients

        self.reference = IntergrowthReference(reference)
        self._parameters = read_intergrowth_coefficients()

    def zscore(
        self,
        indicator: IntergrowthIndicator | str,
        measurement: float,
        age: float,
        sex: str,
    ) -> float:
        c = self._parameters
        indicator = IntergrowthIndicator(indicator)
        if not isinstance(sex, str) or sex.strip().upper() not in ("M", "F", "MALE", "FEMALE"):
            raise ValueError("Sex must be M or F")
        male = sex.strip().upper() in ("M", "MALE")
        if isinstance(measurement, bool) or isinstance(age, bool):
            raise ValueError("Age and measurement must be real numbers")
        y, x = float(measurement), float(age)
        if not (math.isfinite(y) and math.isfinite(x) and y > 0):
            raise ValueError("Age and measurement must be finite, measurement positive")
        if indicator is IntergrowthIndicator.WEIGHT_FOR_LENGTH:
            if self.reference is not IntergrowthReference.PRETERM_POSTNATAL:
                raise ValueError("Weight-for-length is not available for very-preterm birth")
            if not 35 <= x <= 65:
                raise ValueError("Length must be within 35–65 cm")
            dm = x / 10
            log_dm = math.log(dm)
            cube = dm**3
            if male:
                mu = c["wfl_male_mu_base"] + (c["wfl_male_mu_power"] - c["wfl_male_mu_log"] * log_dm) / dm**2
                sigma = math.exp(c["wfl_male_sigma_base"] + c["wfl_male_sigma_cube"] * cube)
            else:
                mu = (
                    c["wfl_female_mu_base"]
                    + c["wfl_female_mu_divisor"] / dm
                    - c["wfl_female_mu_sqrt"] / math.sqrt(dm)
                )
                sigma = (
                    c["wfl_female_sigma_base"]
                    - c["wfl_female_sigma_cube"] * cube
                    + c["wfl_female_sigma_logcube"] * cube * log_dm
                )
            return (y - mu) / sigma
        if self.reference is IntergrowthReference.PRETERM_POSTNATAL:
            if not 27 <= x <= 64:
                raise ValueError("Postmenstrual age must be 27–64 weeks")
            if indicator is IntergrowthIndicator.WEIGHT:
                mu = (
                    c["post_weight_mu_base"]
                    - c["post_weight_mu_sqrt"] * math.sqrt(x)
                    - c["post_weight_mu_inverse"] / x**2
                    + c["post_weight_mu_male"] * male
                )
                sigma = (
                    c["post_weight_sigma_base"]
                    + (c["post_weight_sigma_power"] - c["post_weight_sigma_log"] * math.log(x)) / x**2
                )
                y = math.log(y)  # weight in kg
            elif indicator is IntergrowthIndicator.LENGTH:
                mu = (
                    c["post_length_mu_base"]
                    - c["post_length_mu_inverse"] / x**2
                    + c["post_length_mu_age"] * x
                    + c["post_length_mu_male"] * male
                )
                sigma = (
                    c["post_length_sigma_base"]
                    + (c["post_length_sigma_inverse"] - c["post_length_sigma_log"] * math.log(x)) / x**2
                )
                y = math.log(y)
            else:
                mu = c["post_head_mu_base"] - c["post_head_mu_inverse"] / x + c["post_head_mu_male"] * male
                sigma = (
                    c["post_head_sigma_base"]
                    + c["post_head_sigma_inverse"] / x**2
                    - c["post_head_sigma_age"] / x
                )
        else:
            if not 168 <= x <= 230:
                raise ValueError("Gestational age must be 168–230 days")
            weeks = x / 7
            if indicator is IntergrowthIndicator.WEIGHT:
                mu = (
                    c["birth_weight_mu_base"]
                    + c["birth_weight_mu_sqrt"] * math.sqrt(weeks)
                    + c["birth_weight_mu_male"] * male
                )
                sigma = math.sqrt(c["birth_weight_sigma_variance"])
                y = math.log(y)
            elif indicator is IntergrowthIndicator.LENGTH:
                mu = (
                    c["birth_length_mu_base"]
                    + c["birth_length_mu_week"] * weeks
                    + c["birth_length_mu_male"] * male
                )
                sigma = math.sqrt(c["birth_length_sigma_variance"])
            else:
                mu = (
                    c["birth_head_mu_base"] + c["birth_head_mu_week"] * weeks + c["birth_head_mu_male"] * male
                )
                sigma = math.sqrt(c["birth_head_sigma_variance"])
        if not math.isfinite(sigma) or sigma <= 0:
            raise ValueError("Invalid reference standard deviation")
        return (y - mu) / sigma
