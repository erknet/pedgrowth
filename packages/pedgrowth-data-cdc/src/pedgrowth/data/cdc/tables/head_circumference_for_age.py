from pedgrowth.tables import TableType

from .base import CdcGrowthTable


class CdcHcForAge(CdcGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.HeadCircumferenceForAge

    def get_file_name(self) -> str:
        return "cdc_head_circumference_for_age"

    def get_csv_url(self) -> str:
        return "https://www.cdc.gov/growthcharts/data/zscore/hcageinf.csv"
