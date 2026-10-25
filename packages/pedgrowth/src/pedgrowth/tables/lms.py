"""Reference LMS parameters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LMS:
    l: float
    m: float
    s: float
    sigma: float | None = None
    p95: float | None = None
