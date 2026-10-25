# Source provenance and redistribution rights audit

**Reviewed 17 October 2026. This is a source inventory and rights triage, not
a legal opinion or a grant of redistribution permission.**

All 33 researched WHO/CDC reference tables (optional sources excluded from MIT core distributions) are listed individually in
`REFERENCE_REUSE_RIGHTS.json`, with upstream URL, upstream raw SHA-256,
normalized CSV SHA-256, reference edition, origin and rights assessment.
The official-source live verification confirmed **33/33 source hashes and
normalized datasets identical** to official current downloads. Seven
INTERGROWTH equation-based models are tracked separately. Tests enforce the
one-to-one match between the source manifest and the rights inventory.

## WHO — clearance required before unrestricted public distribution

The 24 WHO 2006/2007 datasets are subject to source-specific WHO intellectual
property and data reuse conditions. General WHO dataset terms sometimes
permit reuse and redistribution for public health purposes; those terms are
**not automatically equivalent** to the licensing of older WHO publications
and specialized reference tables. WHO's 2016+ publication licensing does
not retroactively establish a CC-BY license for every 2006/2007 table.

Thus the status of unrestricted public reuse, particularly commercial
redistribution and compiled/reformatted binary LMS data, remains
**not legally established in this project**. Obtain an explicit
source-applicable rights determination, and, where required, written WHO
permission. Do not represent the BSD-3-Clause package license as extending
WHO rights.

Official terms: https://www.who.int/about/policies/publishing/copyright
WHO data policy: https://www.who.int/about/policies/publishing/data-policy/terms-and-conditions
Older-publication conditions: https://www.who.int/about/policies/publishing/open-access
Permission requests: https://www.who.int/about/policies/publishing/permissions

## CDC — public-domain baseline with conditions

Most CDC/NCHS materials created by the US Federal Government are public
domain in the United States, with CDC-required attribution and non-endorsement.
The agency cautions that third-party components, foreign jurisdictions and
derivative/reformatting conditions may differ. The project's data are exact
normalized scientific coefficients and are available from CDC free of charge.
The package's own third-party notice identifies CDC and specifically states
there is no institutional endorsement.

Official reuse terms: https://www.cdc.gov/Other/imagereuse.html
Published data: https://www.cdc.gov/growthcharts/cdc-data-files.htm
2022 extended BMI: https://www.cdc.gov/growthcharts/extended-bmi-data-files.htm

## INTERGROWTH — use is documented, derivative redistribution not settled

The official INTERGROWTH-21st project states that practitioners can download
and **use** its growth charts freely, while directing modification requests
to its team. This does not by itself determine unrestricted public or
commercial redistribution of every adapted reference product.

The seven supported Python tables independently implement published
equations; no `gigs` GPL-3.0 R source is redistributed in the wheel. The
original unmodified, hash-verified R v0.5.2 implementation is downloaded
only as a validation tool in CI. The numerical outputs from this independent
implementation are used as test oracles.

Official standards: https://intergrowth21.tghn.org/standards-tools/
Gigs project: https://github.com/ropensci/gigs

## Separate publication and scientific-data rights checks

The **code-only provider publication** workflow runs, for example:

    python scripts/verify_reference_rights.py --enforce-publication --providers cdc

It checks source manifests, independently declared code licenses, rights
notices, and the exclusion of numerical reference datasets. It does not
require a signed data-redistribution clearance because the current wheels
and sdists do not contain the scientific coefficients.

For a **future release bundling numerical scientific data**, run:

    python scripts/verify_reference_rights.py --enforce-data-redistribution --providers cdc

This separate check remains fail-closed until
`docs/REFERENCE_PUBLICATION_CLEARANCE.json` contains a signed,
source-fingerprint-bound rights assessment. No automated check grants
permission to download, transform, redistribute, or use upstream reference
data. The audit-only command `python scripts/verify_reference_rights.py`
validates provenance without granting rights.

## Additional evidence from WHO copyright-holder R releases

The WHO-published GPL R packages anthro and anthroplus embed the actual WHO 2006/2007 coefficient arrays. Across pedgrowth's 24 WHO datasets, 28,228 numerical LMS records match those arrays exactly with zero coefficient mismatches. Another 420 rows lie beyond anthro's age domain. This strengthens the evidence for a GPL-compliant WHO coefficient data route but does not independently authorize unrestricted BSD re-licensing or redistribution of WHO website downloads. See [WHO_R_COEFFICIENT_RIGHTS_AUDIT.md](WHO_R_COEFFICIENT_RIGHTS_AUDIT.md).

## Optional-source separation implemented

The pedgrowth 1.0.0 **MIT-only core wheel and sdist** contain no WHO/CDC
coefficients or INTERGROWTH fitted parameters, and the four independent
provider distributions are also code-only. Each provider includes a
source-rights notice, source hashes, and acquisition code. When a requested
reference is absent from the cache, its provider obtains and verifies the
upstream data at first use, subject to the upstream terms. The optional
`from pedgrowth.data import download_missing_dependencies` initializer
fetches installed providers' missing resources in advance.
See OPTIONAL_REFERENCE_SOURCES.md and PROVIDER_LICENSE_RELEASE.md for the
40-reference source-by-source evidence. A successful technical check is
not a license to download, redistribute, or reuse upstream datasets.

**Important:** The development Git checkout still contains audited
source snapshots and fixtures used for private scientific validation;
making that repository public remains separately gated until all
tracked/staged source data have been removed or cleared.
