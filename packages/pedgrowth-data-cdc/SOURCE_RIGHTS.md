# pedgrowth-data-cdc — code licensing and CDC reference provenance

## Scope of the MIT license

The **independently authored Python code** and provider-specific normalization
logic in this extension are licensed under the MIT License, copyright © 2026
ERKNet. See [LICENSE](LICENSE) and the package metadata.

**The MIT license does not grant copyright ownership over, or relicense, the
original CDC scientific datasets.** The `SOURCE_RIGHTS.json`,
`SOURCE_LICENSE_MATRIX.json`, and `SOURCES.json` files document source
attribution, individual URLs, pinned SHA-256 hashes, and review status.

## How the data are obtained

Published wheels and source distributions are **code-only**: they do not include
any source coefficient CSV files or compiled LMSB reference tables. When a
calculation needs a missing CDC table, the extension attempts to download its
pinned CSV directly from the original CDC source URL, verifies the exact
downloaded bytes, normalizes the numeric columns without altering their
values, and validates the generated LMSB digest before saving the result in a
user cache. Other tables remain available if one source cannot be downloaded.

The optional `pedgrowth.data.download_missing_dependencies()` attempts all
registered reference sources in advance, warns about unavailable files, and
retries failures on later calls.

## CDC agency materials and obligations

The U.S. Centers for Disease Control and Prevention (CDC) states that
most information on its website is U.S. federal public-domain material,
but exceptions include contractor/grantee works and licensed third-party
materials; international copyright rules may differ.

For uses of CDC public-domain content, CDC instructs users to:

- Attribute the CDC/agency as the source (e.g., **Source: CDC**).
- State clearly that this package is **not endorsed by CDC, HHS, or the
  United States Government**.
- Preserve substantive scientific content. The local conversion changes
  file representation, not the reference equations or coefficient values.
- Disclose that the original resources are **available free of charge**
  on CDC's official website.
- Do not use CDC/HHS agency names, marks, or logos to suggest endorsement.

The original reference datasets are published on these official pages:

- [CDC 2000 Growth Charts LMS files](https://www.cdc.gov/growthcharts/cdc-data-files.htm)
- [CDC 2022 Extended BMI-for-Age](https://www.cdc.gov/growthcharts/extended-bmi-data-files.htm)
- [CDC Use of Agency Materials](https://www.cdc.gov/other/agencymaterials.html)

This project is neither affiliated with nor endorsed by the CDC, HHS, or the
U.S. Government. This software and these references are not, by themselves,
a clinical diagnosis.

## Publication status and third-party software

**Original CDC access and use rights review is still pending.** Code-only
publication checks confirm that no numerical CDC references ship in the
wheel or sdist, but do not authorize access, downstream use or automated
downloads. A future data-inclusive build requires separate signed review.
This is not a legal opinion.

The independent `cdcanthro` R validation package is GPL-3.0-only.
Its program license does not relicense CDC reference data or change
this extension's independently authored Python code license.
