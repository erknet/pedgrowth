from pedgrowth.tables import Sex, TableType

from .base import WhoRightSkewedGrowthTable


class WhoWeightForAgeGirls(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.WeightForAge

    def get_file_name(self) -> str:
        return "who_weight_for_age_girls"

    # def get_csv_url(self) -> str:
    #    return 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Girls-Weight-for-age%20Percentiles.csv'

    def get_xslx_url(self) -> str:
        return "https://cdn.who.int/media/docs/default-source/child-growth/child-growth-standards/indicators/weight-for-age/expanded-tables/wfa-girls-zscore-expanded-tables.xlsx"

    def get_table_sex(self) -> Sex | None:
        return Sex.Female
