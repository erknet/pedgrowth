from pedgrowth.tables import Sex, TableType

from .base import WhoRightSkewedGrowthTable


class WhoBmiForAgeGirls(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.BodyMassIndexForAge

    def get_file_name(self) -> str:
        return "who_bmi_for_age_girls"

    def get_xslx_url(self) -> str:
        return "https://cdn.who.int/media/docs/default-source/child-growth/child-growth-standards/indicators/body-mass-index-for-age/expanded-tables/bfa-girls-zscore-expanded-tables.xlsx"

    def get_table_sex(self) -> Sex | None:
        return Sex.Female
