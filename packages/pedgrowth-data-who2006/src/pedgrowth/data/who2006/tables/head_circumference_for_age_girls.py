from pedgrowth.tables import Sex, TableType

from .base import WhoGrowthTable


class WhoHcForAgeGirls(WhoGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.HeadCircumferenceForAge

    def get_file_name(self) -> str:
        return "who_head_circumference_for_age_girls"

    # def get_csv_url(self) -> str:
    #    return 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Girls-Head-Circumference-for-age-Percentiles.csv'

    def get_xslx_url(self) -> str:
        return "https://cdn.who.int/media/docs/default-source/child-growth/child-growth-standards/indicators/head-circumference-for-age/expanded-tables/hcfa-girls-zscore-expanded-tables.xlsx"

    def get_table_sex(self) -> Sex | None:
        return Sex.Female
