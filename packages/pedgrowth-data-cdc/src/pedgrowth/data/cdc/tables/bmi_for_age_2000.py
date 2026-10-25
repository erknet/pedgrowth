"""Original (nonextended) CDC 2000 BMI-for-age LMS table."""

from pedgrowth.tables import TableType

from .base import CdcGrowthTable


class CdcBmiForAge2000(CdcGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.BodyMassIndexForAge

    def get_file_name(self) -> str:
        return "cdc_bmi_for_age_2000"

    def get_csv_url(self) -> str:
        return "https://www.cdc.gov/growthcharts/data/zscore/bmiagerev.csv"
