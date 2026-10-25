from pedgrowth.tables import TableType

from .base import CdcGrowthTable


class CdcBmiForAge(CdcGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.BodyMassIndexForAge

    def get_file_name(self) -> str:
        return "cdc_bmi_for_age"

    def get_csv_url(self) -> str:
        return "https://www.cdc.gov/growthcharts/data/extended-bmi/bmi-age-2022.csv"

    def get_col_index_sigma(self) -> int | None:
        return 5
