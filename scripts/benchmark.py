"""Repeatable scalar-vs-NumPy throughput comparison, not a fragile CI gate.

Run: python scripts/benchmark.py --count 100000
Requires the optional '[vector]' extras.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pedgrowth import GrowthChartsCalculator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100_000)
    args = parser.parse_args()
    if not 1 <= args.count <= 2_000_000:
        parser.error("--count must be between 1 and 2,000,000")
    calculator = GrowthChartsCalculator()
    measurements = np.full(args.count, 10.4, dtype=np.float64)
    ages = np.full(args.count, 22.45, dtype=np.float64)

    # Warm both code paths before timing to exclude import/cold-load overhead.
    calculator.wfa(10.4, 22.45, "M")
    calculator.zscores_numpy("wfa", measurements[:1], ages[:1], "M")

    start = perf_counter()
    result_scalar = [calculator.wfa(10.4, 22.45, "M") for _ in range(args.count)]
    scalar_seconds = perf_counter() - start

    start = perf_counter()
    result_vector = calculator.zscores_numpy("wfa", measurements, ages, "M")
    vector_seconds = perf_counter() - start
    if any(
        scalar is None or abs(float(vector) - scalar) > 1e-12
        for vector, scalar in zip(result_vector, result_scalar, strict=True)
    ):
        raise AssertionError("Vector and scalar results disagree")

    print(f"Observations: {args.count:,}")
    print(f"Scalar: {scalar_seconds:.4f} s ({args.count / scalar_seconds:,.0f} obs/s)")
    print(f"NumPy/SciPy: {vector_seconds:.4f} s ({args.count / vector_seconds:,.0f} obs/s)")
    print(f"Speedup: {scalar_seconds / vector_seconds:.1f}x")


if __name__ == "__main__":
    main()
