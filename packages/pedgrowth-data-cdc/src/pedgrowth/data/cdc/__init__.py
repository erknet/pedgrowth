"""Independent growth reference extension."""
# SPDX-License-Identifier: MIT

from pedgrowth.registry import ReferenceProvider, ReferenceRegistry

from .downloader import initialize_data
from .plans import (
    CdcClinicalPlan as CdcClinicalPlan,
)
from .plans import (
    CdcPlan as CdcPlan,
)
from .plans import (
    CdcWithWhoFallbackPlan as CdcWithWhoFallbackPlan,
)
from .plans import (
    WhoWithCdcFallbackPlan as WhoWithCdcFallbackPlan,
)
from .selection import accept as accept_cdc
from .selection import batch_accept as batch_accept_cdc
from .selection import batch_candidates as batch_candidates_cdc
from .selection import candidates as candidates_cdc
from .tables import CDC_TABLES


def register(registry: ReferenceRegistry) -> None:
    registry.register(
        ReferenceProvider(
            name="cdc",
            family="cdc",
            module=__name__,
            tables=tuple(CDC_TABLES),
            initialize_data=initialize_data,
            download_resource=initialize_data,
            candidate_policy=candidates_cdc,
            accept_policy=accept_cdc,
            batch_candidate_policy=batch_candidates_cdc,
            batch_accept_policy=batch_accept_cdc,
            plans={
                "cdc": CdcPlan,
                "cdc_clinical": CdcClinicalPlan,
                "cdc_with_who_fallback": CdcWithWhoFallbackPlan,
                "who_with_cdc_fallback": WhoWithCdcFallbackPlan,
            },
        )
    )
