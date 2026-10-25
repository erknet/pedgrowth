# WHO baseline coefficients and the licensing of official R packages

Reviewed 17 October 2026. This is a technical source/rights assessment,
not a legal opinion or permission to republish source datasets under BSD.

## Stronger positive evidence from WHO itself

WHO is listed as a copyright holder and package maintainer of the CRAN
packages **anthro 1.1.0** (GPL-3) and **anthroplus 1.1.0**
(GPL version 3 or later). Importantly, these packages contain the
actual numeric reference coefficient data, not merely calculation routines:

- anthro embeds nine WHO 2006 LMS coefficient data frames in R/sysdata.rda.
- anthroplus embeds three WHO 2007 LMS coefficient data frames in R/sysdata.rda.
- Both datasets include boys' and girls' coefficients.
- An independent direct numeric comparison verified that pedgrowth's **24/24
  WHO baseline tables** contain **28,228 LMS records identical** to WHO's
  officially published, GPL-licensed R datasets, with **zero mismatches**.
- An additional **420 records** (30 age days for each of 14 tables) in
  pedgrowth's original-source WHO 2006 data exceed the age-domain records
  supplied by anthro. They cannot be tied to anthro's GPL distribution
  by this direct-match evidence.

Repeat the precise audit using the original R packages:

    Rscript --vanilla scripts/verify_r_validation_licenses.R
    Rscript --vanilla scripts/verify_who_r_embedded_tables.R

The dedicated independent GitHub Actions validation workflow now runs the
WHO-embedded-coefficient comparison. It checks a fixed 24-table / 28,228
identical-row / 420 extra-row / zero-mismatch expectation and fails on drift.

## What we can infer

1. **Running the standards for clinical and research calculations** is an
   intended use explicitly encouraged by WHO. The official R packages and
   public scientific publications are compelling supporting evidence.
2. **WHO-authorized redistribution exists in at least one form:** WHO itself
   publishes the same coefficient arrays in GPL-licensed software with WHO
   identified as a copyright holder. This is much stronger than relying on
   a third-party package alone.
3. **A possible GPL-data reuse route exists.** If the numerical data in
   these precise package copies fall under WHO's GPL grant, a recipient may
   have rights to reuse and redistribute these particular copies in
   compliance with the GPL and appropriate attribution/source terms.
   Any rights-holder carve-outs, and whether an independently formatted,
   repackaged binary LMS table remains a separately covered work,
   need review.
4. **An unqualified BSD-data reuse grant cannot be inferred.** The
   pedgrowth reference files are derived from WHO's separate official
   dataset downloads, and the R GPL releases do not themselves state
   that these downloads may be relicensed under BSD-3-Clause, nor establish
   the same license for the 420 additional records.

## Why other package precedents are weaker

- The GPL-3 cdcanthro R package bundles CDC growth data and WHO LMS
  coefficients (cdc_ref_data and who_ref_data). Its authors are not the
  original WHO copyright holder. Its availability demonstrates reuse,
  not an independent sublicensing grant for third parties.
- The GPL >= 3 gigs package bundles published INTERGROWTH-21st curve and
  coefficient data, and documents original study sources. The copyright
  holder named for the software is the London School of Hygiene & Tropical
  Medicine; the package metadata does not explicitly establish the rights
  to sublicense every underlying consortium dataset under BSD.
- CDC's U.S. Government reference tables generally have a stronger
  public-domain/attribution basis independently of these R packages.
  A CDC publication of WHO coefficients does not convert the underlying
  WHO-origin tables into U.S. public-domain material.

## WHO's differing website data terms matter

The WHO **data.who.int** terms say that its own datasets are generally
CC BY 4.0 unless otherwise specified, with additional conditions.

The WHO **www.who.int** data-compilation terms provide a narrower
public-health-purpose grant with modification and commercial-promotion
restrictions. The 2006/2007 coefficient spreadsheets used by pedgrowth
came from **www.who.int**. We have not established that these particular
files are covered by the data.who.int CC BY grant.

Direct license from the WHO-owned GPL package may be a more useful
source-specific evidence route than either broad website statement.

## Data are not identical to code

Mathematical facts and numbers can be outside ordinary copyright
protection depending on jurisdiction and context, but a compiled reference
database can carry separate selection/arrangement rights or EU sui-generis
database rights for substantial extraction/re-utilization. This should
not be reduced to the assertion that every digit of an LMS table is
copyrighted, or that every table is automatically public domain.

GNU GPL FAQ also distinguishes the software license from output that does
not reproduce protected program text. Numerical z-scores independently
calculated by an R tool generally do not inherit its GPL automatically.
A wholesale copy of an **embedded data table**, however, is a separate
redistribution question.

## Recommendation for pedgrowth

Keep the MIT license **for independently authored Python code** and keep
WHO/CDC/INTERGROWTH source attribution and data-license notices distinct.
Use the WHO-official R coefficient match as strong additional evidence
when asking the WHO maintainer/rights team for a narrow clarification:

> WHO distributes the identical growth-standard LMS data in WHO-authored
> GPL R packages anthro and anthroplus. Can these numeric coefficients be
> repackaged and redistributed, with attribution, as separate reference
> data inside a free BSD-licensed Python library on GitHub and PyPI,
> including commercial downstream users? If not under BSD, do the R
> packages confer a GPL-compliant, separately licensed data-distribution
> pathway, including source-form availability and compiled LMS tables?

If a valid GPL grant for the precise data can be established, it may be
possible to ship the reference data under appropriate separate GPL notices
while keeping independently written Python code BSD licensed. Whether
their integration constitutes aggregation or a single combined covered
work warrants qualified counsel's review.

The publication permission check remains fail-closed pending a documented
source-specific conclusion; it is not changed by the new evidence.

## Reference sources

- https://cran.r-project.org/package=anthro
- https://cran.r-project.org/package=anthroplus
- https://github.com/WorldHealthOrganization/anthro
- https://github.com/WorldHealthOrganization/anthroplus
- https://www.who.int/about/policies/publishing/data-policy/terms-and-conditions
- https://data.who.int/about/data/terms-and-conditions
- https://www.gnu.org/licenses/gpl-faq.en.html#WhatCaseIsOutputGPL
- https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:31996L0009

### Update to implementation
The Python engine has now switched to MIT, with all numerical WHO/CDC and INTERGROWTH sources excluded from the public core wheel and sdist. The GPL-R-package evidence remains informative when evaluating future separately licensed data distribution, not an automatic license for the new source packages.
