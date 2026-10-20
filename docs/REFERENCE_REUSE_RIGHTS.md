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

## Publication gate

The release workflow executes:

    python scripts/verify_reference_rights.py --enforce-publication

It fails unless `docs/REFERENCE_PUBLICATION_CLEARANCE.json` is created
from `REFERENCE_PUBLICATION_CLEARANCE.example.json` and records explicit
clearance independently for `who2006`, `who2007`, `cdc` and `intergrowth` under
`unrestricted_public_python_distribution`, signed by a named legal reviewer
and supported by reviewable evidence and the exact provider reference-manifest
SHA-256 for the planned release. For an independent provider build, use
`--enforce-publication --providers cdc` (or other selected provider names).
The default five-distribution release checks all four independently.

A manifest with `status: pending` does not clear publication, and no
clearance is created automatically. The audit-only command:

    python scripts/verify_reference_rights.py

checks source and rights metadata without implying permission.

Actual clearance decisions require the rights holder or appropriately
qualified human counsel. **Do not mark the permissions cleared solely
because automated validation is green.**

## Additional evidence from WHO copyright-holder R releases

The WHO-published GPL R packages anthro and anthroplus embed the actual WHO 2006/2007 coefficient arrays. Across pedgrowth's 24 WHO datasets, 28,228 numerical LMS records match those arrays exactly with zero coefficient mismatches. Another 420 rows lie beyond anthro's age domain. This strengthens the evidence for a GPL-compliant WHO coefficient data route but does not independently authorize unrestricted BSD re-licensing or redistribution of WHO website downloads. See [WHO_R_COEFFICIENT_RIGHTS_AUDIT.md](WHO_R_COEFFICIENT_RIGHTS_AUDIT.md).

## Optional-source separation implemented

The pedgrowth 1.0.0 **MIT-only core wheel and sdist** contain no WHO/CDC
coefficient snapshots or INTERGROWTH fitted numerical parameters.
Each reference provider has a separately declared installation group and
a rights-status entry in the packaged data/SOURCE_LICENSES.json metadata.
A user may install locally and lawfully obtained, normalized files using
the explicit reference installer after reviewing the terms.
Installation is never automatic and a flag indicating the user's
acknowledgement does not grant redistribution rights.
See OPTIONAL_REFERENCE_SOURCES.md and PROVIDER_LICENSE_RELEASE.md for the
40-reference file-by-file evidence and corresponding editable CSV source packages.

**Important:** The development Git checkout still contains audited
source snapshots and fixtures used for private scientific validation;
making that repository public remains separately gated until all
tracked/staged source data have been removed or cleared.
