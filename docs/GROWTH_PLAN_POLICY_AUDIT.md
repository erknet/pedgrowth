# Formal GrowthPlan policy audit

**Audit date: 2026-10-17.** All six named plans were reviewed for source
eligibility, age and coordinate limits, measurement-position normalization,
fallback precedence, direct-table separation and scalar/NumPy agreement.

An independent hand-curated expectation matrix is in
`tests/fixtures/policy_review.csv`, accompanied by
`policy_review_manifest.json` with its SHA-256 and a source URL for each
policy category. Its 68 entries do **not** come from the application's
`resolve()` logic. The suite `test_formal_plan_policy.py` evaluates
reference IDs, index conversion, measurement offsets and vector results.
`test_plan_policy_properties.py` additionally tests every indicator and
both sexes across 21 ages for all five WHO/CDC plans, checks factory parity,
and verifies fallback precedence independently.

## Decision table

| Plan | Specified behavior | Audit | Scientific applicability |
| --- | --- | --- | --- |
| `WhoPlan` | WHO 2006 child standards, then WHO 2007 where available; age-aware length/height and WFL/WFH position conversion | **Pass** | WHO reference choice, not an automatic corrected-age or prematurity policy |
| `CdcPlan` | Select an available CDC table only, using the existing overlap precedence | **Pass** | **Not a clinical US age-selection policy**: CDC infant tables can be resolved below 24 months |
| `CdcWithWhoFallbackPlan` | CDC if table eligible, otherwise WHO; calculation failure does not trigger fallback | **Pass** | Explicit user-defined precedence, not recommended clinical standard |
| `WhoWithCdcFallbackPlan` | WHO if table eligible, otherwise CDC; calculation failure does not trigger fallback | **Pass** | Explicit user-defined precedence, not recommended clinical standard |
| `CdcClinicalPlan` | WHO for <24 months, CDC for >=24 and <240 months, age-appropriate position adjustment, no BMI-for-age below 24 | **Pass within the documented supported clinical policy** | Based on US CDC/AAP recommendation, **not** a full clinical assessment algorithm |
| `IntergrowthPlan` | Postnatal INTERGROWTH-only tables, 27-64 postmenstrual weeks; WFL requires length 35-65 cm **and** postmenstrual-age context | **Pass for computational selection** | Only suitable when caller independently establishes eligibility for preterm postnatal follow-up; no automatic birth-chart or WHO transition |

The separate INTERGROWTH very-preterm **at-birth** tables accept gestational
age in days (168-230), but are **not** a postnatal `GrowthPlan`. This is
intentional and tested.

## Official reference decisions

### United States CDC clinical sequence

The CDC and AAP recommend WHO growth standards from birth to <2 years and
CDC reference charts from 2 to 20 years. Under 24 months, BMI-for-age is
not a CDC-recommended screening chart. At the two-year transition, measurements
change from recumbent length to standing height, and classification changes
must be interpreted cautiously.

- Source: https://www.cdc.gov/growth-chart-training/hcp/overview/recommended.html
- Source: https://www.cdc.gov/growth-chart-training/hcp/using-growth-charts/who-using.html
- Source: https://www.cdc.gov/growth-chart-training/hcp/using-bmi/summary.html

`CdcClinicalPlan` intentionally selects the package's CDC 2022 Extended BMI
table for BMI at >=24 months. Its LMS computation matches standard CDC LMS
below P95, and the extended tail takes effect above P95. CDC recommends
using the 2022 Extended BMI chart **above P97**, and states that either
chart may be used between P95 and P97. Accordingly, the package's
95th-97th percentile handling is an **explicit permitted chart choice**,
not an implementation of a strict P97 switch. Analyses demanding strict
2000-chart behavior in this overlap should use `CdcBmiForAge2000` directly
and document the decision.

The optional reference tables for head circumference, arm circumference and
skinfolds have indicator-specific limited ranges. Clinical eligibility is
never inferred solely from the existence of a source table.

### WHO reference and size-for-age

WHO's 2006 child standard applies to 0-60 months, and the WHO 2007
reference supplies BMI/height for 61-228 months and weight for 61-120
months. The package does not extrapolate beyond an available coefficient
domain. An extremely narrow interval may remain uncovered between the
terminal 2006 daily-grid coordinate (converted to months) and the first
WHO 2007 monthly coordinate. This **must be reported as unavailable**,
not silently filled by selecting an unvalidated source.

The WHO AnthroPlus guide specifies recumbent length below 24 months and
standing height from 24 months, using a 0.7-cm correction when the recorded
measurement position differs. `WhoPlan`, the WHO fallback stage of
user-precedence plans, and `CdcClinicalPlan` now use this age-aware
reference selection when chronological age is supplied. When an age-free
length or height coordinate is supplied to a research-oriented plan,
the caller's explicit WFL/WFH request determines the source family.

- Source: https://www.who.int/tools/growth-reference-data-for-5to19-years
- Source: https://www.who.int/docs/default-source/child-growth/growth-reference-5-19-years/who-anthroplus-manual.pdf

### INTERGROWTH-21st preterm postnatal

The `ig_png` reference supports WFA/LFA/HCFA between 27-64 weeks of
postmenstrual age and WFL indexed by 35-65 cm. The `IntergrowthPlan`
now requires PMA metadata for all indicators, including WFL. It cannot
determine whether a patient was born preterm from PMA alone: birth gestational
age and cohort eligibility are outside this interface. The plan never
automatically switches to WHO after 64 weeks PMA and cannot transform
chronological age into PMA without additional data.

- Source: https://docs.ropensci.org/gigs/reference/index.html
- Source: https://github.com/ropensci/gigs

## Findings and changes made during this audit

1. **WHO WFL/WFH wrong-age selection**: `WhoPlan` could prioritize a
   chart matching the caller's label even when age implied the other
   measurement position. It now selects the WHO reference appropriate to
   available chronological age, then applies the validated 0.7 cm conversion.
2. **Scalar/NumPy divergence**: after the WHO selection fix, the batch
   resolver initially still selected the original table in mixed-age cases.
   The vector masks were corrected and the independent expected-table
   matrix confirms parity.
3. **INTERGROWTH WFL population context**: the postnatal plan used to
   allow WFL with length alone or a non-postmenstrual age. The plan now
   requires valid PMA in 27-64 weeks; direct equation tables remain
   separately selectable by their model coordinates.
4. **User-defined versus clinical policies**: the two fallback plans and
   CDC-only plan are documented as explicit source preferences rather
   than mislabeled clinical recommendations.

## Remaining clinical review, not software test defects

- Clinical use of a chart for a particular diagnosis, infant born preterm,
  or condition-specific population requires external eligibility information.
- WHO daily-grid ages near the 60/61-month interface need a documented
  exact-date convention in the study; the package does not synthesize
  missing reference coefficients.
- The age-adjustment conversion uses the library's documented
  30.4375-day month convention rather than actual calendar birthdays.
- The 0.7 cm height/length correction and head-circumference rules may
  differ from study-specific measurement protocols. Choose and record
  a single protocol, and retain the selected reference's provenance.
- Additional fetal and term-newborn INTERGROWTH standards remain outside
  the implemented feature set.

The audited implementation is appropriate for numerical research analyses
*within its documented scope*; this is not blanket clinical certification.
