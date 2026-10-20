from pedgrowth.tables import Sex, TableType

from .base import WhoRightSkewedGrowthTable


class WhoWeightForHeightGirls(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.WeightForHeigt

    def get_file_name(self) -> str:
        return "who_weight_for_height_girls"

    # def get_csv_url(self) -> str:
    #    return 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/growthcharts/WHO-Girls-Weight-for-length-Percentiles.csv'

    def get_xslx_url(self) -> str:
        return "https://cdn.who.int/media/docs/default-source/child-growth/child-growth-standards/indicators/weight-for-length-height/expanded-tables/wfh-girls-zscore-expanded-tables.xlsx?sfvrsn=daac732c_8"

    def get_table_sex(self) -> Sex | None:
        return Sex.Female
