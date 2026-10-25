"""Equation-based INTERGROWTH references; birth references are direct tables only."""

from __future__ import annotations

from pedgrowth.architecture import AgeDefinition
from pedgrowth.policies import InterpolationPolicy
from pedgrowth.provenance import ReferenceProvenance
from pedgrowth.tables import ReferenceTable, Sex, TableType

from .intergrowth import IntergrowthCalculator, IntergrowthIndicator, IntergrowthReference


class IntergrowthEquationTable(ReferenceTable):
    """Equation-backed table without LMS coefficient loading."""

    reference: IntergrowthReference
    indicator: IntergrowthIndicator

    def __init__(self) -> None:
        self._calculator = IntergrowthCalculator(self.reference)
        self.override_sha256 = None

    def get_provenance(self) -> ReferenceProvenance:
        import json
        from importlib import resources

        from pedgrowth.provenance import ReferenceProvenance

        metadata = json.loads(
            resources.files("pedgrowth.data.intergrowth")
            .joinpath("data", "INTERGROWTH_SOURCES.json")
            .read_text()
        )
        return ReferenceProvenance(
            name=self.get_file_name(),
            standard="INTERGROWTH-21st",
            reference_version="Published regression equations verified against gigs",
            source_url="https://intergrowth21.tghn.org/standards-tools/",
            source_sha256=None,
            data_sha256=str(metadata["sha256"]),
            snapshot_date=None,
        )

    def get_table_type(self) -> TableType:
        return {
            IntergrowthIndicator.WEIGHT: TableType.WeightForAge,
            IntergrowthIndicator.LENGTH: TableType.LengthForAge,
            IntergrowthIndicator.HEAD_CIRCUMFERENCE: TableType.HeadCircumferenceForAge,
            IntergrowthIndicator.WEIGHT_FOR_LENGTH: TableType.WeightForLength,
        }[self.indicator]

    def get_file_name(self) -> str:
        return f"intergrowth_{self.reference.value}_{self.indicator.value}"

    def get_min_range(self) -> float:
        if self.indicator is IntergrowthIndicator.WEIGHT_FOR_LENGTH:
            return 35.0
        return 27.0 if self.reference is IntergrowthReference.PRETERM_POSTNATAL else 168.0

    def get_max_range(self) -> float:
        if self.indicator is IntergrowthIndicator.WEIGHT_FOR_LENGTH:
            return 65.0
        return 64.0 if self.reference is IntergrowthReference.PRETERM_POSTNATAL else 230.0

    def age_coordinate(self, age: float, definition: AgeDefinition) -> float:
        from pedgrowth.architecture import AgeType, AgeUnit

        expected = (
            AgeType.POSTMENSTRUAL
            if self.reference is IntergrowthReference.PRETERM_POSTNATAL
            else AgeType.GESTATIONAL
        )
        if getattr(definition, "type", None) is not expected:
            raise ValueError(f"Direct INTERGROWTH table requires {expected.value} age")
        unit = definition.unit
        days = age * {AgeUnit.DAYS: 1, AgeUnit.WEEKS: 7, AgeUnit.MONTHS: 30.4375, AgeUnit.YEARS: 365.25}[unit]
        return days / 7 if expected is AgeType.POSTMENSTRUAL else days

    def calculate_zscore(
        self,
        index_value: float,
        measurement: float,
        sex: Sex | None = None,
        interpolation: InterpolationPolicy = InterpolationPolicy.NEAREST,
    ) -> float:
        if sex is None:
            raise ValueError("INTERGROWTH requires sex")
        return self._calculator.zscore(self.indicator, measurement, index_value, sex.value)


class IntergrowthPretermWeightForAge(IntergrowthEquationTable):
    reference = IntergrowthReference.PRETERM_POSTNATAL
    indicator = IntergrowthIndicator.WEIGHT


class IntergrowthPretermLengthForAge(IntergrowthEquationTable):
    reference = IntergrowthReference.PRETERM_POSTNATAL
    indicator = IntergrowthIndicator.LENGTH


class IntergrowthPretermHeadCircumferenceForAge(IntergrowthEquationTable):
    reference = IntergrowthReference.PRETERM_POSTNATAL
    indicator = IntergrowthIndicator.HEAD_CIRCUMFERENCE


class IntergrowthPretermWeightForLength(IntergrowthEquationTable):
    reference = IntergrowthReference.PRETERM_POSTNATAL
    indicator = IntergrowthIndicator.WEIGHT_FOR_LENGTH


class IntergrowthVeryPretermBirthWeightForAge(IntergrowthEquationTable):
    reference = IntergrowthReference.VERY_PRETERM_BIRTH
    indicator = IntergrowthIndicator.WEIGHT


class IntergrowthVeryPretermBirthLengthForAge(IntergrowthEquationTable):
    reference = IntergrowthReference.VERY_PRETERM_BIRTH
    indicator = IntergrowthIndicator.LENGTH


class IntergrowthVeryPretermBirthHeadCircumferenceForAge(IntergrowthEquationTable):
    reference = IntergrowthReference.VERY_PRETERM_BIRTH
    indicator = IntergrowthIndicator.HEAD_CIRCUMFERENCE


INTERGROWTH_POSTNATAL_TABLES = (
    IntergrowthPretermWeightForAge,
    IntergrowthPretermLengthForAge,
    IntergrowthPretermHeadCircumferenceForAge,
    IntergrowthPretermWeightForLength,
)
