"""CDC-only, WHO/CDC fallback, and clinical growth plans."""

from pedgrowth.architecture import AgeDefinition
from pedgrowth.plans import GrowthPlan
from pedgrowth.tables import TableType


class CdcPlan(GrowthPlan):
    def __init__(self) -> None:
        super().__init__(("cdc",))


class CdcWithWhoFallbackPlan(GrowthPlan):
    def __init__(self) -> None:
        super().__init__(("cdc", "who"))


class WhoWithCdcFallbackPlan(GrowthPlan):
    def __init__(self) -> None:
        super().__init__(("who", "cdc"))


class CdcClinicalPlan(GrowthPlan):
    def __init__(self) -> None:
        super().__init__(("who", "cdc"), mode="clinical")

    def _batch_family_masks(
        self,
        kind: TableType,
        age_months: object | None,
        definition: AgeDefinition | None,
        count: int,
    ) -> dict[str, object]:
        import numpy as np
        from pedgrowth.architecture import AgeType

        if age_months is None or definition is None:
            raise ValueError(
                "CDC clinical selection requires chronological age even for length-based indicators"
            )
        if definition.type is not AgeType.CHRONOLOGICAL:
            raise ValueError("WHO/CDC postnatal references require chronological age")
        ages = np.asarray(age_months, dtype=float)
        eligible = np.isfinite(ages) & (ages >= 0) & (ages < 240)
        if kind is TableType.BodyMassIndexForAge:
            eligible &= ages >= 24
        return {"who": eligible & (ages < 24), "cdc": eligible & (ages >= 24)}

    def _selected_families(
        self, kind: TableType, age: float | None, definition: AgeDefinition | None
    ) -> tuple[str, ...]:
        import math

        from pedgrowth.architecture import _months
        from pedgrowth.exceptions import DataNotFoundError
        from pedgrowth.tables import TableType

        if age is None or definition is None:
            raise ValueError(
                "CDC clinical selection requires chronological age even for length-based indicators"
            )
        months = _months(float(age), definition)
        if not math.isfinite(months) or months >= 240:
            raise DataNotFoundError("CDC clinical charts cover ages below 240 months")
        if kind is TableType.BodyMassIndexForAge and months < 24:
            raise DataNotFoundError("CDC clinical BMI-for-age is not recommended under 24 months")
        return ("who",) if months < 24 else ("cdc",)
