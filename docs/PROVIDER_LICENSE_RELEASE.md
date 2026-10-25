# Source-by-source licensing and reproducibility audit

**Reviewed 19 October 2026.** This is a reproducible rights inventory, not a legal opinion or a blanket redistribution permission. Each provider distribution is separate from the MIT-licensed calculation engine. The independently authored CDC extension code is MIT, copyright ERKNet, while original CDC scientific reference datasets are not relicensed under MIT. WHO 2006 and WHO 2007 remain distinct **scientific** references; WHO 2007 does not cover children below roughly five years of age.

The machine-readable [40-reference licensing matrix](REFERENCE_LICENSE_MATRIX.json) covers **18 WHO 2006 LMS files, 6 WHO 2007 LMS files, 9 CDC LMS files, and 7 INTERGROWTH equation models**. It records each original URL and SHA-256, the relevant R reference package, numerical overlap when independently verified, candidate rights basis and gaps. The corresponding entries are installed under each provider's `data/SOURCE_LICENSE_MATRIX.json`; the native build checks exact equality against the audited matrix, while wheel RECORD metadata hashes the packaged files.

## Conclusions by provider

| Provider | Original source and independently verified data | License position | What must still be established |
| --- | --- | --- | --- |
| WHO 2006 (`anthro` 1.1.0) | WHO official spreadsheets; **28,228 WHO 2006/2007 R-embedded matching rows in total** | WHO is named a copyright holder in official GPL-3 R distribution, which contains numerical LMS arrays | Establish applicability of WHO's embedded R GPL grant to extracted/transformed datasets; **420 website-only WHO 2006 rows (14 files × 30) are outside that R package** |
| WHO 2007 (`anthroplus` 1.1.0) | WHO official published spreadsheets; **all six WHO 2007 files match R package coefficient rows** | WHO is identified as copyright holder; WHO R package GPL ≥3 | Verify data component covered by GPL and any permission/attribution and corresponding-source requirements |
| CDC 2000/2022 | Original CDC published LMS/sigma sources and published percentile values | US federal authored CDC materials generally public domain **within the US**, barring individual exclusions | Verify every numerical file is federal-authored, third-party exclusions, and international applicability; packaging bootstrap is independently MIT |
| INTERGROWTH (`gigs` 0.5.2) | Published regression equations and fitted parameters, independently checked against `gigs` R outputs | `gigs` GPL ≥3, LSHTM project involvement and INTERGROWTH project endorsement of `gigs` | Confirm the specific parameters were licensed for GPL redistribution by their rights holders and that articles' publisher restrictions do not govern their reproduction |

The package license `MIT` is **not** an assertion that WHO or INTERGROWTH data are MIT. Likewise `gigs` software being GPL does not itself relicense third-party articles or datasets.

### Authoritative links

- WHO copyright-holder R package: [anthro 1.1.0](https://cran.r-project.org/src/contrib/anthro_1.1.0.tar.gz), [anthroplus 1.1.0](https://cran.r-project.org/src/contrib/anthroplus_1.1.0.tar.gz); official [WHO data conditions](https://www.who.int/about/policies/publishing/data-policy/terms-and-conditions) and [WHO permissions](https://www.who.int/about/policies/publishing/permissions).
- CDC: [use of agency materials](https://www.cdc.gov/other/agencymaterials.html), [original CDC LMS data](https://www.cdc.gov/growthcharts/cdc-data-files.htm), [extended BMI data](https://www.cdc.gov/growthcharts/extended-bmi-data-files.htm).
- INTERGROWTH: [official project endorsement of gigs](https://intergrowth21.com/news/new-r-package-standardising-fetal-neonatal-and-child-growth-assessment), [gigs R source](https://github.com/ropensci/gigs/tree/v0.5.2/R), [2015 postnatal paper](https://doi.org/10.1016/S2214-109X(15)00163-1), [2016 very preterm paper](https://doi.org/10.1016/S0140-6736(16)00384-6), [consortium terms](https://intergrowth21.tghn.org/terms/).
- Third-party precedent: [RCPCH growth references](https://github.com/rcpch/growth-references) notes that original provider rights supersede repository licenses; [growthstandards R](https://github.com/ki-tools/growthstandards) is another implementation, not a sublicensing document. Wikimedia reuse of rendered charts is also not a license for all LMS data.

## WHO 2006 additional data are not silently truncated

The script `scripts/verify_who_r_embedded_tables.R`, run against pinned WHO-authored R 1.1.0 packages, compares all 24 WHO tables. It proves 28,228 coefficient records match with no numerical mismatches and 420 WHO 2006 records are outside the embedded R tables' coordinate domain. Exactly 14 files have 30 additional rows apiece. These rows remain essential to the currently implemented WHO age-range semantics, so this packaging change **does not discard or silently relicense them**.

The 420 rows must receive a separately applicable source-data grant, or the scientific domain and regression tests must be explicitly changed in a future reviewed release. A whole-file GPL declaration is inappropriate until this is addressed.

## Editable source form and executable-code separation

All WHO and CDC distributions now contain code, source URLs, audits,
normalization logic and SHA-256 digests but **no scientific coefficient CSVs
or compiled LMSB files**. INTERGROWTH distributes source hashes and parameter reconstruction
code, not its fitted regression parameters. The end-user cache contains
data obtained separately from upstream sources. Downloading and locally
transforming references still requires compliance with source terms.


The original R-package GPL text is shipped for source attribution/verification, but it is not automatically the operational license for independently produced packaging code. The CDC provider's independently written Python code is MIT (copyright ERKNet),
but this does **not** place original CDC numeric datasets under MIT; WHO/INTERGROWTH bootstraps retain their chosen GPL expressions. Each artifact also includes source-by-source evidence, validation-generator scripts and pinned source hashes.

## Separate publication checks: code-only Python distributions vs datasets

The current WHO 2006, WHO 2007, CDC and INTERGROWTH extension wheels and
source distributions contain **no scientific numerical coefficients**.
They contain Python implementation code, source URLs/checksums, provenance,
attribution and source-use notices. Publishing this code does **not**
redistribute reference datasets. No signed permission to redistribute
those *absent* datasets is required by the code-only packaging validator.

The provider workflow requires a matching PyPI core version, independently
declared Python code license, audited source manifests, source-use notices,
no obsolete research-only marker, and wheel/sdist scans excluding scientific
coefficient CSV, LMSB, Excel, and fitted parameter JSON files.

To verify code-only publication:

~~~bash
python scripts/verify_reference_rights.py --enforce-publication --providers who2006
python scripts/verify_reference_rights.py --enforce-publication --providers cdc
python scripts/build_distributions.py --mode publication --components who2006 --output-dir .local/publication-who2006
~~~

The absence of bundled datasets is **not a grant** for subsequent downloading,
conversion, commercial use, or handling of upstream resources. Source-specific
terms and attribution remain documented and may restrict use.

For any **future release that bundles scientific numerical data**, a separate
signed human review remains mandatory:

~~~bash
python scripts/verify_reference_rights.py --enforce-data-redistribution --providers who2006
~~~

The signed review template
[REFERENCE_PUBLICATION_CLEARANCE.example.json](REFERENCE_PUBLICATION_CLEARANCE.example.json)
applies to that data-redistributing scenario, **not** today's code-only wheels.
An R software GPL license does not automatically govern original study data.

**Publishing the historical research monorepo remains a separate decision**:
private snapshots, fixtures and old Git objects may contain scientific data.
Only the reviewed code-only tree is suitable for public publication.

## Validation and source integrity

```bash
python -m pytest -q
python scripts/refresh_data.py --check
Rscript --vanilla scripts/verify_who_r_embedded_tables.R
python scripts/build_distributions.py --mode local
python scripts/check_data_distributions.py .local/split-distributions
```

Frozen R-generated fixtures are enumerated in `validation/source_data/SOURCE_LICENSES.json` with the exact scripts and source-specific numeric validation method, and in the packaged `SOURCE_RIGHTS.md`.
