"""Data-free tests suitable for public MIT-core CI without research fixtures."""

from __future__ import annotations

import pytest
from pedgrowth import GrowthChartsCalculator
from pedgrowth.data import download_missing_dependencies
from pedgrowth.policies import InterpolationPolicy
from pedgrowth.tables import ReferenceTable, Sex, TableType


class _SyntheticWeightTable(ReferenceTable):
    def get_table_type(self) -> TableType:
        return TableType.WeightForAge

    def get_file_name(self) -> str:
        return "synthetic_weight"

    def get_min_range(self) -> float:
        return 0.0

    def get_max_range(self) -> float:
        return 200.0

    def calculate_zscore(
        self,
        index_value: float,
        measurement: float,
        sex: Sex | None = None,
        interpolation: InterpolationPolicy = InterpolationPolicy.NEAREST,
    ) -> float:
        return (measurement - 10.0) / 2.0


def test_clean_core_contract_with_explicit_reference() -> None:
    from pedgrowth import AgeDefinition, AgeType, AgeUnit

    calc = GrowthChartsCalculator(table=_SyntheticWeightTable())
    assert (
        calc.calculate(
            indicator="wfa",
            measurement=12.0,
            sex="M",
            age=12.0,
            age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
        ).zscore
        == 1.0
    )
    assert calc.calculate_numpy.__call__


def test_optional_provider_acquisition_api_imports_without_network() -> None:
    assert callable(download_missing_dependencies)


def test_explicit_table_mismatch_is_rejected() -> None:
    from pedgrowth import AgeDefinition, AgeType, AgeUnit
    from pedgrowth.exceptions import DataNotFoundError

    calc = GrowthChartsCalculator(table=_SyntheticWeightTable())
    with pytest.raises(DataNotFoundError):
        calc.calculate(
            indicator="hcfa",
            measurement=12.0,
            sex="F",
            age=12.0,
            age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
        )
