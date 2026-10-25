"""Independent growth reference extension."""
# SPDX-License-Identifier: GPL-3.0-only

from pedgrowth.registry import ReferenceProvider, ReferenceRegistry

from .downloader import initialize_data
from .plans import WhoPlan as WhoPlan
from .selection import accept as accept_who
from .selection import batch_accept as batch_accept_who
from .selection import batch_candidates as batch_candidates_who
from .selection import candidates as candidates_who
from .tables import WHO_TABLES


def register(registry: ReferenceRegistry) -> None:
    registry.register(
        ReferenceProvider(
            name="who2006",
            family="who",
            module=__name__,
            tables=tuple(WHO_TABLES),
            initialize_data=initialize_data,
            download_resource=initialize_data,
            plans={"who": WhoPlan},
            candidate_policy=candidates_who,
            accept_policy=accept_who,
            batch_candidate_policy=batch_candidates_who,
            batch_accept_policy=batch_accept_who,
        )
    )
