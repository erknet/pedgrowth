"""WHO postnatal reference selection."""

from pedgrowth.plans import GrowthPlan


class WhoPlan(GrowthPlan):
    def __init__(self) -> None:
        super().__init__(("who",))
