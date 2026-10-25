# Validation coverage and release gate

**This is not a claim of full independent clinical validation.** Numerical
oracles must be sourced from an external publication or reference implementation,
not calculated by GrowthCharts and then used as its own expected values.

## Current per-table evidence

- **CDC (9/9 tables):** 8,744 published P3/P5/P50/P95 observations
  downloaded from official CDC files and frozen under
  `tests/fixtures/official_percentiles`. `manifest.json` records official
  source URL, SHA-256 of the official downloaded source, snapshot hash and
  observation count. Tests verify all available observations and compare the
  z-score against the independent standard-normal percentile definition.
  Official source hashes are checked when refreshing fixtures.
- **INTERGROWTH (7/7 implemented equation tables):** published rounded
  tables **and** 4,970 independent continuous calculations from the unmodified
  upstream R `gigs` v0.5.2 source files, including random coordinates,
  extreme measurements, domain endpoints, and both sexes. The three upstream
  R sources are SHA-256 pinned, and Python is compared at 2e-10 absolute
  z-score tolerance.
- **WHO (24/24 tables):** 520 baseline and 3,384 further independently
  calculated WHO R observations from anthro 1.1.0 and anthroplus 1.1.0,
  including extreme +/-4 SD, near-boundary and off-grid reference coordinates.
  The 3,888-case matrix retains 504 officially unavailable results beyond
  WHO Anthro's age limit, which are explicitly verified instead of discarded.
- **CDC extended BMI:** 180 independent cdcanthro R observations, and stable
  high-z tail calculations tested against SciPy; 18 CDC R unavailable cases
  at the 240-month age boundary are retained.
- **WHO measurement position:** 12 official WHO R records for standing and
  recumbent measurements, with two independently scored indicators each.

`python scripts/audit_validation_coverage.py` prints the current status of
all 40 implemented tables. No unvalidated table is silently marked validated.

## Plans

`tests/fixtures/plan_resolution.csv` is a manually curated table-selection
oracle. `tests/test_plan_oracle.py` checks the expected table identifier for
WHO, CDC, fallback, and CDC clinical policies (including missing references
and the 24-month boundary). The expanded independently curated
`policy_review.csv` covers all six named plans, including INTERGROWTH,
with additional boundary-grid invariants. See
`GROWTH_PLAN_POLICY_AUDIT.md`. This checks **reference resolution**, separately
from the z-score algorithm. `tests/test_plan_batch_matrix.py` checks scalar,
NumPy and Pandas agreement; such agreement alone is not an independent oracle.

## Independent execution

`scripts/export_official.R` and `scripts/validate_official.py` provide a
separate R-backed comparison, run by the official-validation CI workflow.
The independent validation workflow regenerates WHO baseline, WHO extended,
WHO measurement-position and CDC BMI numerical oracles on R runners.

## Missing before scientific sign-off

1. Scientific and clinical expert review of applicable chart selection,
   age corrections, measurement protocols and reference limitations.
2. Extended INTERGROWTH newborn and fetal reference families are not
   implemented or validated.
3. Source redistribution/licensing review, expert review of clinical
   eligibility/age adjustment, and externally executed release CI.

Official reference documents: https://www.cdc.gov/growthcharts/cdc-data-files.htm,
https://www.cdc.gov/growthcharts/extended-bmi-data-files.htm,
https://www.who.int/tools/child-growth-standards/standards,
https://intergrowth21.tghn.org/postnatal-growth-preterm-infants/.
