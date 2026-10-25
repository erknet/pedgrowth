"""Additional WHO 2006 anthropometric measures from 3 months to 5 years."""

from pedgrowth.tables import Sex, TableType

from .base import WhoRightSkewedGrowthTable


class WhoMuacBoys(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.MidUpperArmCircumferenceForAge

    def get_file_name(self) -> str:
        return "who_muac_for_age_boys"

    def get_table_sex(self) -> Sex:
        return Sex.Male


class WhoMuacGirls(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.MidUpperArmCircumferenceForAge

    def get_file_name(self) -> str:
        return "who_muac_for_age_girls"

    def get_table_sex(self) -> Sex:
        return Sex.Female


class WhoTricepsBoys(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.TricepsSkinfoldForAge

    def get_file_name(self) -> str:
        return "who_triceps_for_age_boys"

    def get_table_sex(self) -> Sex:
        return Sex.Male


class WhoTricepsGirls(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.TricepsSkinfoldForAge

    def get_file_name(self) -> str:
        return "who_triceps_for_age_girls"

    def get_table_sex(self) -> Sex:
        return Sex.Female


class WhoSubscapularBoys(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.SubscapularSkinfoldForAge

    def get_file_name(self) -> str:
        return "who_subscapular_for_age_boys"

    def get_table_sex(self) -> Sex:
        return Sex.Male


class WhoSubscapularGirls(WhoRightSkewedGrowthTable):
    def get_table_type(self) -> TableType:
        return TableType.SubscapularSkinfoldForAge

    def get_file_name(self) -> str:
        return "who_subscapular_for_age_girls"

    def get_table_sex(self) -> Sex:
        return Sex.Female


WHO_ADDITIONAL_TABLES = [
    WhoMuacBoys,
    WhoMuacGirls,
    WhoTricepsBoys,
    WhoTricepsGirls,
    WhoSubscapularBoys,
    WhoSubscapularGirls,
]
