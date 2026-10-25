from pedgrowth.tables import TableType

from .base import CdcGrowthTable


class CdcWeightForHeight(CdcGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.WeightForHeigt

    def get_file_name(self) -> str:
        return "cdc_weight_for_height"

    def get_csv_url(self) -> str:
        return "https://www.cdc.gov/growthcharts/data/zscore/wtstat.csv"
