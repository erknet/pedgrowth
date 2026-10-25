"""Independent growth reference extension."""
# SPDX-License-Identifier: GPL-3.0-or-later

from pedgrowth.registry import ReferenceProvider, ReferenceRegistry

from .downloader import initialize_data
from .plans import Who2007Plan
from .tables import WHO_2007_TABLES


def register(registry: ReferenceRegistry) -> None:
    registry.register(
        ReferenceProvider(
            name="who2007",
            family="who",
            module=__name__,
            tables=tuple(WHO_2007_TABLES),
            initialize_data=initialize_data,
            download_resource=initialize_data,
            plans={"who2007": Who2007Plan},
        )
    )
