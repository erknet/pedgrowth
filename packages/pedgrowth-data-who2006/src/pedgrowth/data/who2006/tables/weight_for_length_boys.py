from pedgrowth.tables import Sex, TableType

from .base import WhoRightSkewedGrowthTable


class WhoWeightForLengthBoys(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.WeightForLength

    def get_file_name(self) -> str:
        return "who_weight_for_length_boys"

    # def get_csv_url(self) -> str:
    #    return 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Boys-Weight-for-length-Percentiles.csv'

    def get_xslx_url(self) -> str:
        return "https://cdn.who.int/media/docs/default-source/child-growth/child-growth-standards/indicators/weight-for-length-height/expanded-tables/wfl-boys-zscore-expanded-table.xlsx"

    def get_table_sex(self) -> Sex | None:
        return Sex.Male
