"""Shared provider namespace and optional eager reference initialization.

Providers register their own data loader via pedgrowth.references entry points.
Importing this module never downloads references.
"""

from __future__ import annotations

import warnings
from pkgutil import extend_path as _extend_path

__path__ = _extend_path(__path__, __name__)


def download_missing_dependencies() -> dict[str, int]:
    """Initialize data for every registered extension.

    Only providers with a declared data initializer perform acquisition.
    Installing and importing providers remains side-effect free. Returns the
    number of newly cached resources for each registered provider.
    """
    from pedgrowth.registry import registry

    results: dict[str, int] = {}
    from pedgrowth.exceptions import DataError

    for provider in registry.providers():
        try:
            results[provider.name] = provider.initialize_data() if provider.initialize_data else 0
        except DataError as exc:
            warnings.warn(
                f"Reference provider {provider.name} could not initialize its data: {exc}; "
                "unavailable resources will be retried on next use",
                RuntimeWarning,
                stacklevel=2,
            )
            results[provider.name] = 0
    return results


__all__ = ["download_missing_dependencies"]
