from pedgrowth.tables import TableType

from .base import CdcGrowthTable


class CdcWeightForLength(CdcGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.WeightForLength

    def get_file_name(self) -> str:
        return "cdc_weight_for_length"

    def get_csv_url(self) -> str:
        return "https://www.cdc.gov/growthcharts/data/zscore/wtleninf.csv"
