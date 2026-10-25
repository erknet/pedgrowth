from pedgrowth.tables import TableType

from .base import CdcGrowthTable


class CdcWeightForAgeInfant(CdcGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.WeightForAge

    def get_file_name(self) -> str:
        return "cdc_weight_for_age_0_36"

    def get_csv_url(self) -> str:
        return "https://www.cdc.gov/growthcharts/data/zscore/wtageinf.csv"
