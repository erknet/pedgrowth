"""Deterministic, safe binary LMS format for build-time compilation.

NOT pickle, marshal, eval, or executable Python source. The payload is a
zlib-compressed stream of fixed-width IEEE754 numeric tuples; a SHA-256 of
the normalized CSV is stored in the header to tie the compiled resource
to its audited human-readable source.
"""

from __future__ import annotations

import hashlib
import io
import math
import struct
import zlib
from collections.abc import Mapping
from types import MappingProxyType

from .exceptions import DataError
from .reference_data import MAX_TABLE_ROWS, parse_lms_csv
from .tables.lms import LMS
from .tables.sex import Sex

MAGIC = b"PGLMS02\x00"
HEADER = struct.Struct("<8s32sI")
RECORD = struct.Struct("<Bdddddd")
SEX_TO_CODE = {None: 0, Sex.Male: 1, Sex.Female: 2}
CODE_TO_SEX = {v: k for k, v in SEX_TO_CODE.items()}


def encode_csv(csv_content: bytes) -> bytes:
    """Turn normalized, validated coefficients into deterministic binary data."""
    table = parse_lms_csv(io.StringIO(csv_content.decode("utf-8-sig")), "compiler")
    count = sum(len(items) for items in table.values())
    payload = bytearray()
    for sex in (None, Sex.Male, Sex.Female):
        for index, lms in sorted(table.get(sex, {}).items()):
            payload.extend(
                RECORD.pack(
                    SEX_TO_CODE[sex],
                    index,
                    lms.l,
                    lms.m,
                    lms.s,
                    lms.sigma if lms.sigma is not None else float("nan"),
                    lms.p95 if lms.p95 is not None else float("nan"),
                )
            )
    return HEADER.pack(MAGIC, hashlib.sha256(csv_content).digest(), count) + zlib.compress(
        bytes(payload), level=9
    )


def decode_binary(
    binary: bytes,
    expected_csv_sha256: str | None = None,
) -> Mapping[Sex | None, Mapping[float, LMS]]:
    """Decode bounded, fixed-format numeric records; reject malformed input."""
    if len(binary) < HEADER.size:
        raise DataError("Truncated compiled reference table")
    magic, original_hash, count = HEADER.unpack(binary[: HEADER.size])
    if magic != MAGIC or count == 0 or count > MAX_TABLE_ROWS:
        raise DataError("Invalid compiled reference header")
    if expected_csv_sha256 and original_hash.hex() != expected_csv_sha256:
        raise DataError("Compiled reference does not match its source CSV hash")
    try:
        decomp = zlib.decompressobj()
        needed = count * RECORD.size
        payload = decomp.decompress(binary[HEADER.size :], needed + 1)
        if len(payload) != needed or not decomp.eof or decomp.unused_data or decomp.unconsumed_tail:
            raise DataError("Compiled coefficient payload has incorrect length")
        table: dict[Sex | None, dict[float, LMS]] = {}
        for sex_code, index, l, m, s, sigma, p95 in RECORD.iter_unpack(payload):
            if sex_code not in CODE_TO_SEX:
                raise DataError("Invalid compiled sex code")
            if not all(math.isfinite(x) for x in (index, l, m, s)):
                raise DataError("Nonfinite compiled LMS parameter")
            if index < 0 or m <= 0 or s <= 0:
                raise DataError("Invalid compiled LMS parameter")
            if not math.isnan(sigma) and (not math.isfinite(sigma) or sigma <= 0):
                raise DataError("Invalid compiled sigma")
            if not math.isnan(p95) and (not math.isfinite(p95) or p95 <= m):
                raise DataError("Invalid compiled P95")
            sex = CODE_TO_SEX[sex_code]
            section = table.setdefault(sex, {})
            if index in section:
                raise DataError("Duplicate compiled index")
            section[index] = LMS(
                l,
                m,
                s,
                None if math.isnan(sigma) else sigma,
                None if math.isnan(p95) else p95,
            )
        return MappingProxyType({sex: MappingProxyType(section) for sex, section in table.items()})
    except (zlib.error, ValueError, struct.error) as exc:
        raise DataError(f"Corrupt compiled reference data: {exc}") from exc
