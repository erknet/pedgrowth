"""Independent growth reference extension."""
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from importlib import resources

from pedgrowth.registry import ReferenceProvider, ReferenceRegistry

from .downloader import initialize_data
from .intergrowth import (
    IntergrowthCalculator as IntergrowthCalculator,
)
from .intergrowth import (
    IntergrowthIndicator as IntergrowthIndicator,
)
from .intergrowth import (
    IntergrowthReference as IntergrowthReference,
)
from .intergrowth_tables import (
    INTERGROWTH_POSTNATAL_TABLES,
)
from .intergrowth_tables import (
    IntergrowthPretermHeadCircumferenceForAge as IntergrowthPretermHeadCircumferenceForAge,
)
from .intergrowth_tables import (
    IntergrowthPretermLengthForAge as IntergrowthPretermLengthForAge,
)
from .intergrowth_tables import (
    IntergrowthPretermWeightForAge as IntergrowthPretermWeightForAge,
)
from .intergrowth_tables import (
    IntergrowthPretermWeightForLength as IntergrowthPretermWeightForLength,
)
from .intergrowth_tables import (
    IntergrowthVeryPretermBirthHeadCircumferenceForAge as IntergrowthVeryPretermBirthHeadCircumferenceForAge,
)
from .intergrowth_tables import (
    IntergrowthVeryPretermBirthLengthForAge as IntergrowthVeryPretermBirthLengthForAge,
)
from .intergrowth_tables import (
    IntergrowthVeryPretermBirthWeightForAge as IntergrowthVeryPretermBirthWeightForAge,
)
from .plans import IntergrowthPlan


def register(registry: ReferenceRegistry) -> None:
    digest = json.loads(resources.files(__name__).joinpath("data", "INTERGROWTH_SOURCES.json").read_text())[
        "sha256"
    ]
    registry.register(
        ReferenceProvider(
            name="intergrowth",
            family="intergrowth",
            module=__name__,
            tables=tuple(
                (
                    *INTERGROWTH_POSTNATAL_TABLES,
                    IntergrowthVeryPretermBirthWeightForAge,
                    IntergrowthVeryPretermBirthLengthForAge,
                    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
                )
            ),
            plans={"intergrowth": IntergrowthPlan},
            manifest_name="INTERGROWTH_SOURCES.json",
            additional_resources={"intergrowth_coefficients.json": digest},
            initialize_data=initialize_data,
        )
    )
