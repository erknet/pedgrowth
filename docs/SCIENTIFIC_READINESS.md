# Scientific validation and release-readiness report

Status: comprehensive numerical testing completed for the 40 implemented reference tables. External clinical review, licensing review and remote CI remain necessary before declaring suitability for medical decisions.

## Independent numerical reference sources

| Family | Tables | Independently sourced numerical oracles |
| --- | ---: | --- |
| WHO 2006 and 2007 | 24 | 520 baseline and 3,384 extended WHO anthro 1.1.0 / anthroplus 1.1.0 results |
| CDC 2000 and 2022 | 9 | 8,744 published percentile measurements from official CDC tables |
| CDC 2022 extended BMI (also above) | 1 | 180 independent cdcanthro 0.4.0 numerical results |
| INTERGROWTH preterm postnatal and very-preterm birth | 7 | Published grids plus 4,970 continuous values from hash-verified original gigs R v0.5.2 source, both sexes |
| WHO measurement position (included above) | — | 12 WHO R records yielding 24 z-score comparisons |

The expanded WHO matrix contains 3,888 inputs at boundary and interior coordinates and around +/- 3 and +/- 4 SD. The WHO R software calculated 3,384 values and returned 504 NA values for ages exceeding its 1,826-day computational range. Missing observations are retained and validated as explicitly unavailable rather than omitted. Frozen input/output files and SHA-256 manifests are under tests/fixtures/who_r. The CDC independent R oracle likewise retains 18 NA cases at or beyond 240 months.

The CDC R extended-BMI inverse-normal calculation saturates near z=8.21 for extreme BMI. The library now uses stable log-survival probabilities. Extreme values are checked against SciPy's independent special functions instead of requiring equality to a numerically saturated R result.

## Plan and execution testing

- A separate independently curated 68-case reference-selection matrix covers all six named GrowthPlans. A further exhaustive grid tests all ten indicators over both sexes and clinically important ages for the five WHO/CDC plans. See GROWTH_PLAN_POLICY_AUDIT.md.
- The CDC clinical policy uses WHO below 24 months and CDC from 24 to less than 240 months, with documented 0.7 cm length/height adjustment. WHO-only policies use age-aware WFL/WFH reference selection. INTERGROWTH's postnatal plan now requires 27-64 weeks of PMA even for WFL. Neither policy establishes preterm eligibility from age alone.
- Every implemented table is also tested via the typed NumPy backend against external R or published reference observations, and across scalar/vector evaluation.
- Tests cover reference provenance and source hashes, invalid measurements, sex normalization, no accidental clinical-age conversions, monotonicity, and NaN/error handling.
- Tests verify the integrity of the 33 compiled reference tables in distribution wheels and a scalar-only isolated Python 3.11 wheel installation without NumPy, Pandas, or SciPy.

## Additional validation completed in the final audit

- **Clinical worked examples:** 42 independent scenarios in
  `tests/fixtures/clinical_cases_input.csv` and
  `clinical_cases_expected.csv` (five published CDC vignettes plus 37
  deliberately synthetic pediatric cases independently evaluated by the
  WHO `anthro`, `anthroplus` or CDC `cdcanthro` R software).
  Published cases validate the reported percentile or source transition;
  synthetic cases validate the numerical score against official R.
  The CDC 9-month-old male weighing 9.7 kg must produce approximately
  z=0.207 at the official half-month reference age. The Sam/Olivia
  BMI examples are checked against published 28th and 99.2nd percentiles.
  These tests are not real-patient outcome studies and contain no PHI.
- **Extreme measurements:** expanded scalar/NumPy stress matrix across
  all 33 LMS tables and all seven INTERGROWTH equation models, plus
  the CDC extended-BMI high-survival tail against SciPy, handling of
  tiny positive/subnormal measurements, and explicit rejection of
  nonrepresentable LMS inputs. The historical unhandled OverflowError
  from certain extreme raw LMS powers was corrected to a domain-specific
  InvalidMeasurement. Mathematically valid WHO -3/+3 SD tails remain
  finite without evaluating an overflowing LMS power.
- **Reproducibility:** Python 3.11–3.14 supported; local Linux runs on
  all four interpreters. A new 12-job GitHub workflow covers Linux,
  Windows and macOS on all four Python versions, retains 162
  independently selected reference-output probes per environment and
  fails the build on mismatched reference IDs or numerical drift.
  **Do not claim those remote Windows/macOS jobs have executed until
  the workflow actually runs.**
- **Source and permissions:** 33/33 official live SHA-256 checks and
  normalized coefficients match. Complete per-source rights audit is in
  `REFERENCE_REUSE_RIGHTS.md`, together with the bundled
  `THIRD_PARTY_NOTICES.md`. Code-only provider distribution checks are
  separate from pending upstream reference acquisition/use terms and any
  future redistribution of numerical data.
- **Security:** local dependency audit and sandbox-isolated wheel
  import checks are included alongside ordinary CI.

## Independent R data regeneration

Run the WHO/CDC scripts with R packages anthro, anthroplus and cdcanthro. For INTERGROWTH, the independent R source is taken from the original pinned gigs v0.5.2 release; R package installation is not necessary:

    Rscript scripts/export_who_r_oracles.R tests/fixtures/who_r/inputs.csv /tmp/who-baseline.csv
    Rscript scripts/export_who_r_challenges.R tests/fixtures/who_r/challenges_input.csv /tmp/who-challenges.csv
    Rscript scripts/export_cdc_r_challenges.R tests/fixtures/official_percentiles/cdc_r_bmi_inputs.csv /tmp/cdc-bmi.csv
    Rscript scripts/export_who_r_positions.R tests/fixtures/who_r/position_inputs.csv /tmp/who-positions.csv
    Rscript scripts/export_intergrowth_gigs_r.R tests/fixtures/intergrowth/continuous_inputs.csv /tmp/gigs-continuous.csv /path/to/pinned/gigs-v0.5.2-source
    python scripts/verify_external_r_snapshots.py /tmp/who-baseline.csv /tmp/who-challenges.csv /tmp/cdc-bmi.csv /tmp/who-positions.csv --intergrowth /tmp/gigs-continuous.csv

The commands above reproduce the archived **private-fixture** comparison suite; those input CSVs are deliberately absent from the public checkout. The public official-validation workflow separately reconstructs 24 WHO coefficient tables from pinned official sources in .local, verifies them against WHO R, compares live WHO/CDC numerical outputs, and regenerates 4,970 synthetic INTERGROWTH challenges against SHA-pinned gigs R source. Private frozen-oracle comparisons are explicitly reported as **NOT RUN** when the complete private fixture set is unavailable; their historical results must not be presented as newly revalidated. The workflow uploads only a numerical-data-free summary, not the downloaded source tables or the R-generated numerical results.

## Scientific corrections established by the external checks

1. WHO WFA, MUAC, triceps, and subscapular reference tables use linear WHO tail adjustment beyond +/-3 SD. Historical regression fixtures are kept and flagged as superseded where they conflicted with WHO R.
2. CDC extended BMI uses a stable survival-function method at very high BMI; scalar and vectorized calculations agree.
3. Plan NumPy batches and scalar inputs normalize sex identifiers consistently.
4. CDC clinical selection avoids choosing infant age tables after 24 months, refuses age at or above 240 months, and incorporates measurement-position conversions.
5. Plan and direct-table metadata report the actual available references, not unrelated default tables.
6. Python CI matrix now targets the stated Python 3.11+ minimum.

## Outstanding scientific and release prerequisites

These checks do NOT certify the package for clinical diagnosis, patient treatment, or unattended decisions. Independent clinical and scientific sign-off remains necessary regarding population choice, preterm/corrected age use, measurement and unit protocols, and reference-transition policy. The WHO 2006 coefficient file contains extra rows above the maximum WHO R calculation age; those rows were not validated against WHO Anthro output. The tagged gigs R implementation was instead executed from its unmodified and SHA-pinned source files, yielding 4,970 independently computed continuous z-scores; installing the full gigs package locally was unnecessary. An independently reproduced R-package installation remains a possible further verification step. Full fetal and newborn INTERGROWTH standards are not implemented, and consequently are not validated. Reference redistribution/licensing and actual remote GitHub CI and package-publishing permissions have not been signed off. A local pip-audit scan found no known vulnerabilities, but dependency findings may change over time.

For scientific reporting, record the installed package version, reference ID and version/hash, indicator, measurement position, age definition and unit, interpolation policy, and any data exclusions.

## Official reference documentation

- WHO Child Growth Standards: https://www.who.int/tools/child-growth-standards
- WHO Anthro software: https://www.who.int/tools/child-growth-standards/software
- CDC chart recommendations: https://www.cdc.gov/growth-chart-training/hcp/overview/recommended.html
- CDC extended BMI: https://www.cdc.gov/growthcharts/extended-bmi-data-files.htm
- INTERGROWTH charts: https://intergrowth21.tghn.org/standards-tools/
