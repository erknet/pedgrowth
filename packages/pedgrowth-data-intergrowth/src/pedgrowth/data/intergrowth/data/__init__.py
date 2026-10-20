"""Reference-specific parameter integrity checks (not part of pedgrowth core)."""

from __future__ import annotations

import json
from collections.abc import Mapping

from pedgrowth.exceptions import DataError
from pedgrowth.references import ensure_resource, read_resource


def read_intergrowth_coefficients() -> Mapping[str, float]:
    try:
        payload = read_resource("intergrowth_coefficients.json")
    except DataError:
        import os

        if "PEDGROWTH_REFERENCE_DIR" in os.environ:
            raise
        payload = None
    if payload is None:
        payload = ensure_resource("intergrowth_coefficients.json")
    model = json.loads(payload)
    from importlib import resources

    meta = json.loads(resources.files(__package__).joinpath("INTERGROWTH_SOURCES.json").read_text())
    if not isinstance(model, dict) or set(model) != set(meta["parameter_names"]):
        raise DataError("INTERGROWTH reference schema mismatch")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in model.values()):
        raise DataError("Invalid reference parameter type")
    return model
