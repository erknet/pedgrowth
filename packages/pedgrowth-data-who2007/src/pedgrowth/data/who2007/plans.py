"""WHO 2007 reference plan, registered by its independent provider."""

from pedgrowth.plans import GrowthPlan


class Who2007Plan(GrowthPlan):
    def __init__(self) -> None:
        # WHO plan resolves all installed WHO references, but filter eligibility
        # to this distribution when explicitly requesting the adolescent charts.
        super().__init__(("who",))
        self._tables["who"] = tuple(
            table for table in self._tables["who"] if table.get_file_name().startswith("who2007_")
        )
