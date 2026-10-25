"""Cross-Python/OS reproducibility probe using frozen independent R oracles.

Emits a normalized JSON artifact for comparison across runner architectures.
The probe never generates its own expected measurements or references.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pedgrowth import (  # noqa: E402
    AgeDefinition,
    AgeType,
    AgeUnit,
    GrowthChartsCalculator,
)
from pedgrowth.data.cdc import CdcPlan  # noqa: E402
from pedgrowth.data.cdc.tables import CDC_TABLES  # noqa: E402
from pedgrowth.data.intergrowth.intergrowth_tables import (  # noqa: E402
    INTERGROWTH_POSTNATAL_TABLES,
    IntergrowthEquationTable,
    IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    IntergrowthVeryPretermBirthLengthForAge,
    IntergrowthVeryPretermBirthWeightForAge,
)
from pedgrowth.data.who2006 import WhoPlan  # noqa: E402
from pedgrowth.tables import GrowthTable, Sex  # noqa: E402

from tests.reference_sets import WHO_TABLES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "tests/fixtures"


def observations() -> dict[str, dict[str, object]]:

    out: dict[str, dict[str, object]] = {}
    who: dict[str, GrowthTable] = {}
    cdc: dict[str, GrowthTable] = {}
    for who_factory in WHO_TABLES:
        factory: Callable[[], GrowthTable] = who_factory
        candidate = factory()
        who[candidate.get_file_name()] = candidate
    for cdc_factory in CDC_TABLES:
        cdc_constructor: Callable[[], GrowthTable] = cdc_factory
        candidate = cdc_constructor()
        cdc[candidate.get_file_name()] = candidate
    with (ROOT / "who_r/expected.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    for name, table in sorted(who.items()):
        selected = [row for row in rows if row["table"] == name and row["expected"]]
        for i, row in enumerate((selected[0], selected[len(selected) // 2], selected[-1])):
            score = table.calculate_zscore(
                float(row["coordinate"]),
                float(row["measurement"]),
                Sex(row["sex"]),
            )
            if not math.isfinite(score):
                raise AssertionError("Nonfinite scalar reference score")
            if abs(score - float(row["expected"])) >= 0.03:
                raise AssertionError(f"WHO reference mismatch: {name}")
            out[f"who:{name}:{i}"] = {"reference_id": name, "z": score}

    for name, table in sorted(cdc.items()):
        with (ROOT / "official_percentiles" / f"{name}.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        selected = [r for r in rows if r["percentile"] == "p50"]
        for i, row in enumerate((selected[0], selected[len(selected) // 2], selected[-1])):
            score = table.calculate_zscore(
                float(row["coordinate"]),
                float(row["measurement"]),
                Sex.Male if row["sex"] == "1" else Sex.Female,
            )
            if not math.isfinite(score) or abs(score) >= 0.035:
                raise AssertionError(f"CDC published percentile mismatch: {name}")
            out[f"cdc:{name}:{i}"] = {"reference_id": name, "z": score}

    ig_table_classes = (
        *INTERGROWTH_POSTNATAL_TABLES,
        IntergrowthVeryPretermBirthWeightForAge,
        IntergrowthVeryPretermBirthLengthForAge,
        IntergrowthVeryPretermBirthHeadCircumferenceForAge,
    )
    ig_tables: dict[str, IntergrowthEquationTable] = {}
    for ig_factory in ig_table_classes:
        candidate_ig = ig_factory()
        ig_tables[candidate_ig.get_file_name()] = candidate_ig
    with (ROOT / "intergrowth/continuous_expected.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    for name, ig_model in sorted(ig_tables.items()):
        family = ig_model.reference.value
        indicator = ig_model.indicator.value
        selected = [r for r in rows if r["family"] == family and r["indicator"] == indicator]
        for i, row in enumerate((selected[0], selected[len(selected) // 2], selected[-1])):
            score = ig_model.calculate_zscore(
                float(row["coordinate"]),
                float(row["measurement"]),
                Sex(row["sex"]),
            )
            if not math.isfinite(score):
                raise AssertionError("Nonfinite scalar reference score")
            if abs(score - float(row["expected"])) >= 2e-10:
                raise AssertionError(f"INTERGROWTH R mismatch: {name}")
            out[f"intergrowth:{name}:{i}"] = {"reference_id": name, "z": score}

    with (ROOT / "clinical_cases_expected.csv").open(newline="") as f:
        cases = list(csv.DictReader(f))
    for row in cases:
        calc = GrowthChartsCalculator(plan=CdcPlan() if row["reference"] == "cdc" else WhoPlan())
        clinical_result = calc.calculate(
            indicator=row["indicator"],
            sex=row["sex"],
            age=float(row["age"]),
            age_definition=AgeDefinition(
                AgeType.CHRONOLOGICAL,
                AgeUnit(row["age_unit"]),
            ),
            coordinate=float(row["coordinate"]) if row["coordinate"] else None,
            measurement=float(row["measurement"]),
        )
        if not math.isfinite(clinical_result.zscore):
            raise AssertionError("Nonfinite clinical example score")
        out[f"clinical:{row['id']}"] = {
            "reference_id": clinical_result.reference_id,
            "z": clinical_result.zscore,
        }
    if len(out) < 160:
        raise AssertionError(f"Insufficient independent reference scenarios: {len(out)}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "platform": platform.system(),
        "machine": platform.machine(),
        "observations": observations(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        f"Reproducibility probe: {result['python']} {result['platform']} — "
        f"{len(result['observations'])} independent-source scenarios"
    )


if __name__ == "__main__":
    main()
