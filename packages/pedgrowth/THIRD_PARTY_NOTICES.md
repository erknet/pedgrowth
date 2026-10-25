# Third-party scientific-reference notices

## Python code

The independently authored pedgrowth calculation engine is released under
**MIT**. The MIT license does **not** extend to third-party scientific
reference datasets or authorize reuse outside their source-specific terms.

The core wheel and source distribution do **not** contain WHO or CDC LMS
coefficient tables or INTERGROWTH fitted numerical parameters. They
contain metadata describing potential reference sources and their integrity
hashes. Source licensing remains governed by the originating provider.

See `pedgrowth/data/SOURCE_LICENSES.json` and
`docs/OPTIONAL_REFERENCE_SOURCES.md`.

## World Health Organization (WHO)

WHO Child Growth Standards (2006) and WHO Growth Reference (2007)
coefficient sources have independent copyright and reuse conditions.
WHO itself publishes related data in its GPL R validation packages
`anthro` and `anthroplus`, but that does not automatically authorize
redistribution of separately downloaded data under MIT. Separate reference
installation and original attribution are required. Unrestricted
redistribution rights have not been documented in this project.

- Source: https://www.who.int/tools/child-growth-standards/standards
- Copyright: https://www.who.int/about/policies/publishing/copyright
- Data conditions: https://www.who.int/about/policies/publishing/data-policy/terms-and-conditions
- Permissions: https://www.who.int/about/policies/publishing/permissions

## US Centers for Disease Control and Prevention (CDC)

CDC 2000 and 2022 growth chart data are generally public domain under
US federal law, with third-party exceptions, international jurisdiction
differences, appropriate attribution and no implication of endorsement.
The optional CDC reference data are not included in the MIT core package.

- Source: https://www.cdc.gov/growthcharts/cdc-data-files.htm
- Source: https://www.cdc.gov/growthcharts/extended-bmi-data-files.htm
- Reuse: https://www.cdc.gov/Other/imagereuse.html

## INTERGROWTH-21st

The published reference equations were independently implemented as
scientific calculation formulas. **All 43 fitted numerical parameters**
have been separated from the MIT engine into an optional, hashed
INTERGROWTH reference file which is not shipped in the core wheel or sdist.
Original data rights and source-specific permissions remain to be established.

- Standards: https://intergrowth21.tghn.org/standards-tools/

## External numerical validators

The R packages `anthro` (GPL-3), `anthroplus` (GPL >= 3),
`cdcanthro` (GPL-3), and `gigs` (GPL >= 3) are independently
installed/executed in GitHub Actions to check numerical results.
They are not imported, vendored or required by the MIT Python runtime.

- Validation source: https://github.com/WorldHealthOrganization/anthro
- Validation source: https://github.com/WorldHealthOrganization/anthroplus
- Validation source: https://github.com/ropensci/gigs

## Historical project attribution

pedgrowth was preceded by the BSD-licensed `pygrowup` project.
The project's current code-origin review found a substantially
independent implementation. Historical contributors are acknowledged in
`AUTHORS` and `PROVENANCE.md`. Should protectable original code be found
during a final human provenance review, its original copyright and
BSD-3-Clause conditions must still be preserved.

**Neither WHO, CDC, UNICEF nor INTERGROWTH endorses pedgrowth.
Growth standards and charts are not standalone clinical diagnoses.**


## Original R GPL and provenance in provider-specific distributions

WHO 2006 uses [anthro](https://cran.r-project.org/package=anthro)
(software `GPL-3.0-only`); WHO 2007 uses
[anthroplus](https://cran.r-project.org/package=anthroplus)
(`GPL-3.0-or-later`); CDC uses
[cdcanthro](https://cran.r-project.org/package=cdcanthro)
(`GPL-3.0-only`); INTERGROWTH uses
[gigs](https://github.com/ropensci/gigs)
(`GPL-3.0-or-later`).

The independently authored minimal Python bootstrap follows the R software GPL
for WHO and INTERGROWTH, but the CDC packaging bootstrap is independently MIT.
Each provider wheel/sdist contains the corresponding original GNU GPL v3 text
as evidence of the separate R validator's software license. Its
README and source notices cite the original scientific tables/equations,
the original R source, and the exact way the values, scientific usage,
validation and packaging were derived or informed by those sources.

**This does not establish that WHO/CDC/INTERGROWTH reference data are
themselves GPL-licensed.** Source-specific data rights remain in
force. See `docs/REFERENCE_R_PACKAGE_PROVENANCE.md`.
