# Original scientific sources, R licenses and derivation of pedgrowth data packages

Reviewed 18 October 2026 against the pinned R package `DESCRIPTION`
metadata and the source references audited in `validation/source_data/SOURCES.json`
and `validation/source_data/INTERGROWTH_SOURCES.json`.

**All four source-data Python distributions identify the upstream R software
license declarations**, but their independent packaging code is licensed
separately. WHO and INTERGROWTH bootstrap code uses the matching GPL-3.0
expression; the CDC provider bootstrap is MIT, because its numerical inputs
come from CDC's independently published source files. Each data package
includes the original R validator's GNU GPL v3 text as
`R_PACKAGE_GPL_LICENSE.txt` (not as a claim that CDC data are GPL).

**This does not independently establish that the original scientific
datasets are themselves GPL-licensed.** Source-file rights and legal grants
from WHO, CDC or INTERGROWTH are a separate question, particularly for
datasets derived from the providers' websites rather than copied from R.
Accordingly, the provider data distributions do **not** yet declare a
whole-package SPDX `License-Expression` on PyPI, and publication is blocked
until documented per-provider clearance exists. No R program source is
embedded in these distributions.

## WHO 2006 — pedgrowth-data-who2006

- **Original R package:** [anthro 1.1.0](https://cran.r-project.org/package=anthro)
- **R software source:** [WorldHealthOrganization/anthro](https://github.com/WorldHealthOrganization/anthro)
- **R package license:** `GPL-3` = SPDX `GPL-3.0-only`
- **Original source tables:** [WHO Child Growth Standards: all indicators](https://www.who.int/tools/child-growth-standards/standards)
- **Original source permissions:** [WHO permissions](https://www.who.int/about/policies/publishing/permissions)

**Provenance:** The 18 packed LMS tables are derived from official WHO 2006
spreadsheet/source datasets and transformed into a normalized and
cryptographically pinned LMS representation. The **WHO-authored R anthro
package embeds matching LMS coefficients** and was used for independent
record-by-record comparison, scientific use interpretation and attribution.
Among combined WHO 2006/2007 source tables, 28,228 records match WHO's
official R packages, with no mismatches. An additional **420 WHO 2006
age-domain records** are found only in the separately published WHO
website tables and cannot be claimed as originating from the R package.

Our Python LMS binary packaging and calculation code are independently
implemented. The R package's original GPL-3 license applies to its R
software and, by project choice, to our minimal provider-package bootstrap,
not automatically to WHO website downloads outside the R-distributed domain.

## WHO 2007 — pedgrowth-data-who2007

- **Original R package:** [anthroplus 1.1.0](https://cran.r-project.org/package=anthroplus)
- **R software source:** [WorldHealthOrganization/anthroplus](https://github.com/WorldHealthOrganization/anthroplus)
- **R package license:** `GPL (>= 3)` = SPDX `GPL-3.0-or-later`
- **Original source tables:** [WHO Growth Reference 2007, ages 5–19 years](https://www.who.int/tools/growth-reference-data-for-5to19-years)
- **Original source permissions:** [WHO permissions](https://www.who.int/about/policies/publishing/permissions)

**Provenance:** The six packed sex-specific BMI-, height- and weight-for-age
LMS tables were normalized from the official WHO 2007 downloadable
reference spreadsheets. The official WHO `anthroplus` R package embeds
the same LMS coefficients and was used to validate the scientific values,
age ranges, algorithms and usage conventions. The resulting independently
encoded LMS binaries have a pinned SHA-256 and per-table upstream URLs.

The `GPL-3.0-or-later` declaration of `anthroplus` is retained for the
minimal provider-package bootstrap. It is not presented as a new license
grant for separate WHO website data files.

## CDC — pedgrowth-data-cdc

- **Original R package:** [cdcanthro 0.4.0](https://cran.r-project.org/package=cdcanthro)
- **R package source:** [CRAN cdcanthro 0.4.0 archive](https://cran.r-project.org/src/contrib/cdcanthro_0.4.0.tar.gz)
- **R package license:** `GPL-3` = SPDX `GPL-3.0-only`
- **Original source tables:** [CDC 2000 Growth Chart LMS data files](https://www.cdc.gov/growthcharts/cdc-data-files.htm)
- **Extended reference:** [CDC 2022 Extended BMI-for-Age LMS/sigma data and methods](https://www.cdc.gov/growthcharts/extended-bmi-data-files.htm)
- **Source reuse information:** [CDC reuse terms](https://www.cdc.gov/Other/imagereuse.html)

**Provenance:** The nine packed CDC tables derive from the CDC's own
published CSVs, including its 2022 Extended BMI data. The independently
GPL-3-licensed R package `cdcanthro` contains CDC/WHO growth calculations
and reference datasets and informed scientific validation, expected
normalization and usage conventions. However, we **do not claim the CDC
2022 extended BMI data originate from `cdcanthro`**.

For the source data itself, U.S. federal public-domain treatment,
attribution, exceptions for third-party content and international law are
considered separately. The independently authored CDC bootstrap is
**MIT-licensed**; `cdcanthro` remains an independently GPL-3.0-only
validation reference, and CDC-origin numerical data do not acquire its GPL.

## INTERGROWTH — pedgrowth-data-intergrowth

- **Original R package:** [gigs 0.5.2](https://github.com/ropensci/gigs/releases/tag/v0.5.2)
- **R software source:** [rOpenSci/gigs](https://github.com/ropensci/gigs)
- **Relevant R equations:** [ig_png.R](https://github.com/ropensci/gigs/blob/v0.5.2/R/ig_png.R) and [ig_vpns.R](https://github.com/ropensci/gigs/blob/v0.5.2/R/ig_vpns.R)
- **R package license:** `GPL (>= 3)` = SPDX `GPL-3.0-or-later`
- **Official charts, calculators and references:** [INTERGROWTH-21st Standards and Tools](https://intergrowth21.tghn.org/standards-tools/)
- **Primary publications:** [Postnatal standards, 2015](https://doi.org/10.1016/S2214-109X(15)00163-1) and [Very preterm size-at-birth reference, 2016](https://doi.org/10.1016/S0140-6736(16)00384-6)
- **Source website conditions:** [INTERGROWTH terms of use](https://intergrowth21.tghn.org/terms/)

**Provenance:** The 43 numerical parameters were transcribed from
INTERGROWTH regression equations, corresponding directly to the original
R `gigs` implementation and grounded in the publications and reference
materials. The `gigs` R source explicitly explains that some fitted
equations were supplied to its authors directly by Dr Eric Ohuma, rather
than appearing in the cited published table. The Python implementation
and packaging are independent, but the *scientific parameter values*
are informed by the original R implementation, the studies and the
official website. Thousands of numerical probes against independently
executed `gigs` methods were used to verify correctness.

The `GPL-3.0-or-later` R license is used for the minimal Python
provider packaging bootstrap and recorded for the R scientific source.
This is **not** evidence that the consortium granted unlimited GPL
redistribution of all website content or fitted equations. In particular,
the official INTERGROWTH website has separate terms for commercial use.

## Reproducing the independent validation data

Each generated `pedgrowth-data-*` package includes `SOURCE_LICENSE_MATRIX.json`,
`SOURCE_RIGHTS.json`, and a `SOURCE_RIGHTS.md` describing both the original
scientific values **and the independent numerical oracle**. The reproducible
scripts and frozen fixture paths are recorded per source in
`validation/source_data/SOURCE_LICENSES.json` under `sources.<family>.validation`; the
build verifies that every family declares these records. The source-specific
license is not inferred from how the oracle was generated.

| Distribution | Independent validation sources | Main generation scripts |
| --- | --- | --- |
| `pedgrowth-data-who2006` | WHO official coefficient tables and `anthro` 1.1.0 R | `refresh_data.py`, `export_who_r_oracles.R`, `export_who_r_challenges.R`, `export_who_r_positions.R` |
| `pedgrowth-data-who2007` | WHO official coefficient tables and `anthroplus` 1.1.0 R | `refresh_data.py`, `export_who_r_oracles.R`, `export_who_r_challenges.R` |
| `pedgrowth-data-cdc` | Official CDC percentiles and `cdcanthro` 0.4.0 R | `refresh_data.py`, `fetch_published_percentiles.py`, `export_cdc_r_challenges.R` |
| `pedgrowth-data-intergrowth` | Original published equations and pinned `gigs` 0.5.2 R | `export_intergrowth_gigs_r.R`, `prepare_intergrowth_r_challenges.py` |

The scripts listed are under `scripts/`, and the exact input/output fixtures are
under `tests/fixtures/`. The R programs are used in development validation only;
no R dependency is required in the Python runtime. Public scientific-data
redistribution remains subject to each origin provider's stated rights.

## Repackaging, integrity and intended use

- `pedgrowth`: independently authored Python calculation engine, MIT.
- `pedgrowth-data-*`: separate source-specific provider distributions;
  the CDC bootstrap is independently MIT, and WHO/INTERGROWTH bootstraps
  follow their respective R software GPL expressions.
- Scientific *values* are derived from the official source tables/equations
  and cross-validated with the relevant original R implementation to the
  degree documented above. Source data licensing remains independent.
- Source tables are normalized, converted to a deterministic binary LMS
  format where applicable, checksummed, and packaged into a completely
  separate Python namespace; INTERGROWTH fitted parameters are stored in
  a separately hash-pinned JSON file.
- `SOURCE_LICENSE_MATRIX.json` inside each provider package records original
  table/expression sources, specific upstream file URLs, R software
  provenance and fingerprints; `SOURCE_RIGHTS.md` states the copyright
  and license limits; `R_PACKAGE_GPL_LICENSE.txt` contains the GPL v3 text.
- The original R code is not linked, translated or included in pedgrowth.
  The R packages are independently installed for scientific comparison.
- Usage and distribution do not imply WHO, CDC, INTERGROWTH or rOpenSci
  endorsement. These standards support clinical assessment but must not
  be interpreted as independent diagnoses.

## Public distribution remains gated

The original R packages' licenses are reproduced truthfully, but using
those software GPL declarations **does not automatically clear public
GitHub/PyPI redistribution** of independently downloaded reference
spreadsheets or separately provided fitted parameters.

The existing signed clearance file and per-source licensing evidence must
still substantiate the actual scientific data rights. Until then,
the four local reference wheels and sdists are **not for public
redistribution**. The monorepo's original research data must not be
made public without review.

See [source rights assessment](REFERENCE_REUSE_RIGHTS.md),
[WHO R coefficient audit](WHO_R_COEFFICIENT_RIGHTS_AUDIT.md), and
[optional-source installation/build design](OPTIONAL_REFERENCE_SOURCES.md).
