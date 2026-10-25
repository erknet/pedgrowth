"""WHO 2007 reference for 61–228 completed months (weight: 61–120)."""

from pedgrowth.tables import Sex, TableType

from .base import WhoGrowthTable, WhoRightSkewedGrowthTable


class Who2007GrowthTable(WhoGrowthTable):
    """Monthly LMS coefficients; unlike WHO 2006 these are already in months."""

    def get_index_factor(self) -> None:
        return None


class Who2007RightSkewedGrowthTable(WhoRightSkewedGrowthTable):
    """WHO 2007 monthly LMS coefficients with WHO tail adjustment."""

    def get_index_factor(self) -> None:
        return None


class Who2007BmiBoys(Who2007RightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.BodyMassIndexForAge

    def get_file_name(self) -> str:
        return "who2007_bmi_for_age_boys"

    def get_table_sex(self) -> Sex:
        return Sex.Male


class Who2007BmiGirls(Who2007RightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.BodyMassIndexForAge

    def get_file_name(self) -> str:
        return "who2007_bmi_for_age_girls"

    def get_table_sex(self) -> Sex:
        return Sex.Female


class Who2007HeightBoys(Who2007GrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.HeightForAge

    def get_file_name(self) -> str:
        return "who2007_height_for_age_boys"

    def get_table_sex(self) -> Sex:
        return Sex.Male


class Who2007HeightGirls(Who2007GrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.HeightForAge

    def get_file_name(self) -> str:
        return "who2007_height_for_age_girls"

    def get_table_sex(self) -> Sex:
        return Sex.Female


class Who2007WeightBoys(Who2007RightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.WeightForAge

    def get_file_name(self) -> str:
        return "who2007_weight_for_age_boys"

    def get_table_sex(self) -> Sex:
        return Sex.Male


class Who2007WeightGirls(Who2007RightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.WeightForAge

    def get_file_name(self) -> str:
        return "who2007_weight_for_age_girls"

    def get_table_sex(self) -> Sex:
        return Sex.Female


WHO_2007_TABLES = [
    Who2007BmiBoys,
    Who2007BmiGirls,
    Who2007HeightBoys,
    Who2007HeightGirls,
    Who2007WeightBoys,
    Who2007WeightGirls,
]
