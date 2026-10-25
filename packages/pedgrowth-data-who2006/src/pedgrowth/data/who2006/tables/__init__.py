from .additional import WHO_ADDITIONAL_TABLES
from .bmi_for_age_boys import WhoBmiForAgeBoys
from .bmi_for_age_girls import WhoBmiForAgeGirls
from .head_circumference_for_age_boys import WhoHcForAgeBoys
from .head_circumference_for_age_girls import WhoHcForAgeGirls
from .length_for_age_boys import WhoLengthForAgeBoys
from .length_for_age_girls import WhoLengthForAgeGirls
from .weight_for_age_boys import WhoWeightForAgeBoys
from .weight_for_age_girls import WhoWeightForAgeGirls
from .weight_for_height_boys import WhoWeightForHeightBoys
from .weight_for_height_girls import WhoWeightForHeightGirls
from .weight_for_length_boys import WhoWeightForLengthBoys
from .weight_for_length_girls import WhoWeightForLengthGirls

WHO_2006_TABLES = [
    WhoHcForAgeBoys,
    WhoHcForAgeGirls,
    WhoLengthForAgeBoys,
    WhoLengthForAgeGirls,
    WhoWeightForAgeBoys,
    WhoWeightForAgeGirls,
    WhoWeightForHeightBoys,
    WhoWeightForHeightGirls,
    WhoWeightForLengthBoys,
    WhoWeightForLengthGirls,
    WhoBmiForAgeBoys,
    WhoBmiForAgeGirls,
]

WHO_TABLES = [*WHO_2006_TABLES, *WHO_ADDITIONAL_TABLES]
