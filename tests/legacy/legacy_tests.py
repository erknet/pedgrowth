"""Legacy WHO survey cross-check, retained for source-distribution regression tests.

Run from a source checkout: python -m pedgrowth.tests
CSV fixtures are intentionally excluded from production wheels.
"""

from __future__ import annotations

import csv
import unittest
from pathlib import Path

from . import GrowthChartsCalculator, Sex
from .exceptions import DataNotFoundError

SURVEY = Path(__file__).resolve().parent / "testdata" / "MySurvey_z_st.csv"
TOLERANCE_Z = 0.3


def _number(row: dict[str, str | None], column: str) -> float | None:
    value = row.get(column)
    return float(value) if value else None


class TestWhoSurvey(unittest.TestCase):
    def test_survey_reference_values(self) -> None:
        calculator = GrowthChartsCalculator()
        comparisons = 0
        with SURVEY.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                sex = Sex.Male if row["GENDER"] == "1" else Sex.Female
                age = _number(row, "agemons")
                weight = _number(row, "WEIGHT")
                height = _number(row, "HEIGHT")
                if age is None or weight is None:
                    continue
                test_cases: tuple[tuple[str, float | None, float | None], ...] = (
                    ("wfa", weight, _number(row, "zwei")),
                    ("lfa", height, _number(row, "zlen")),
                    ("wfl", weight if height is not None else None, _number(row, "zwfl")),
                )
                for indicator, measured, expected in test_cases:
                    if measured is None or expected is None:
                        continue
                    index = height if indicator == "wfl" else age
                    if index is None:
                        continue
                    try:
                        actual = calculator.zscore_for_measurement(
                            indicator,
                            measured,
                            sex,
                            index,
                        )
                    except DataNotFoundError:
                        continue
                    if actual is None:
                        continue
                    comparisons += 1
                    with self.subTest(indicator=indicator, age=age, sex=sex, measurement=measured):
                        self.assertAlmostEqual(actual, expected, delta=TOLERANCE_Z)
        self.assertGreater(comparisons, 100, "Survey regression fixture is unexpectedly empty")


if __name__ == "__main__":
    unittest.main()
