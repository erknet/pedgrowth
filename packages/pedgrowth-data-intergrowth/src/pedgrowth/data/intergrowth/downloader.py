"""Reconstruct INTERGROWTH parameters from pinned upstream gigs R source.

This does not execute R code, extract an archive to disk, or ship regression
constants. The output is checked against the independently audited model hash.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import tarfile
from importlib import resources

from pedgrowth.exceptions import DataError
from pedgrowth.references import (
    fetch_verified_source,
    provider_cache,
    provider_write_lock,
    read_resource,
    save_verified_resource,
)
from pedgrowth.registry import registry

# Names of the published equation terms, in source-expression order.
_POSTNATAL_NAMES = (
    "post_weight_mu_base",
    "post_weight_mu_sqrt",
    "post_weight_mu_inverse",
    "post_weight_mu_male",
    "post_weight_sigma_base",
    "post_weight_sigma_power",
    "post_weight_sigma_log",
    "post_length_mu_base",
    "post_length_mu_inverse",
    "post_length_mu_age",
    "post_length_mu_male",
    "post_length_sigma_base",
    "post_length_sigma_inverse",
    "post_length_sigma_log",
    "post_head_mu_base",
    "post_head_mu_inverse",
    "post_head_mu_male",
    "post_head_sigma_base",
    "post_head_sigma_inverse",
    "post_head_sigma_age",
    "wfl_male_mu_base",
    "wfl_male_mu_power",
    "wfl_male_mu_log",
    "wfl_female_mu_base",
    "wfl_female_mu_divisor",
    "wfl_female_mu_sqrt",
    "wfl_male_sigma_base",
    "wfl_male_sigma_cube",
    "wfl_female_sigma_base",
    "wfl_female_sigma_cube",
    "wfl_female_sigma_logcube",
)
_BIRTH_NAMES = (
    "birth_weight_mu_base",
    "birth_weight_mu_sqrt",
    "birth_weight_mu_male",
    "birth_weight_sigma_variance",
    "birth_length_mu_base",
    "birth_length_mu_week",
    "birth_length_mu_male",
    "birth_length_sigma_variance",
    "birth_head_mu_base",
    "birth_head_mu_week",
    "birth_head_mu_male",
    "birth_head_sigma_variance",
)

# Verify the exact source version, not only a mutable download URL.
_GIGS_URL = "https://api.github.com/repos/ropensci/gigs/tarball/v0.5.2"
_GIGS_SHA256 = "9bf4598fe105ee0c5e39cb6bd3442aa1c127f31c4d4ce7670462b3bed5181bf9"


def _equation_values(archive: tarfile.TarFile, filename: str, function: str) -> list[float]:
    member = next(
        (item for item in archive if item.isfile() and item.name.endswith("/R/" + filename)),
        None,
    )
    if member is None or member.size > 200_000:
        raise DataError("Pinned INTERGROWTH equation source file missing or too large")
    handle = archive.extractfile(member)
    if handle is None:
        raise DataError("Cannot read INTERGROWTH equation source")
    content = handle.read().decode("utf-8")
    marker = function + " <- function"
    if content.count(marker) != 1:
        raise DataError("Unexpected INTERGROWTH equation function layout")
    start = content.index(marker)
    stop = content.find("\n}\n", start)
    if stop < 0:
        raise DataError("Cannot identify INTERGROWTH equation boundaries")
    # Exponents are structural, never fitted parameters; all fitted
    # coefficients in this audited source contain a decimal point.
    section = re.sub(r"\^\(?-?\d+(?:\.\d+)?\)?", "", content[start:stop])
    return [float(value) for value in re.findall(r"(?<![\w.])[-+]?\d+\.\d+(?![\w.])", section)]


def reconstruct_coefficients(source: bytes) -> bytes:
    """Derive 43 numerical values from two pinned, published equation functions."""
    try:
        with tarfile.open(fileobj=io.BytesIO(source), mode="r:gz") as archive:
            postnatal = _equation_values(archive, "ig_png.R", "ig_png_mu_sigma")
            birth = _equation_values(archive, "ig_vpns.R", "ig_vpns_mu_sigma")
    except (tarfile.TarError, UnicodeError, OSError) as exc:
        raise DataError("Invalid pinned INTERGROWTH source archive") from exc
    if len(postnatal) != len(_POSTNATAL_NAMES) or len(birth) != len(_BIRTH_NAMES):
        raise DataError("INTERGROWTH published equation count has changed")
    parameters = dict(zip(_POSTNATAL_NAMES, postnatal, strict=True)) | dict(
        zip(_BIRTH_NAMES, birth, strict=True)
    )
    return (json.dumps(parameters, indent=2, sort_keys=True) + "\n").encode("utf-8")


def initialize_data() -> int:
    provider = registry.provider("intergrowth")
    directory = provider_cache(provider)
    name = "intergrowth_coefficients.json"
    manifest = json.loads(
        resources.files(__package__).joinpath("data", "INTERGROWTH_SOURCES.json").read_text()
    )
    with provider_write_lock(directory):
        try:
            if read_resource(name) is not None:
                return 0
        except DataError:
            if not (directory / name).exists():
                raise
        data = fetch_verified_source(_GIGS_URL, _GIGS_SHA256)
        result = reconstruct_coefficients(data)
        if hashlib.sha256(result).hexdigest() != manifest["sha256"]:
            raise DataError("INTERGROWTH coefficients do not match audited scientific reference")
        save_verified_resource(directory, name, result, manifest["sha256"])
    return 1
