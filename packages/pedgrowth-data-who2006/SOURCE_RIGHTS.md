# pedgrowth-data-who2006 — code-only distribution and reference provenance

## Independently authored Python code

The Python implementation is distributed under **GPL-3.0-only**.
Copyright © 2026 ERKNet for independently authored project code. The
code license does **not** relicense the scientific reference datasets of
WHO Child Growth Standards 2006. The Python package's LICENSE records the code license.

## Acquisition and distribution

The public wheel and source distribution contain implementation code,
verified source URLs, source hashes, provenance/rights metadata and this
notice. **No scientific coefficient CSV, compiled LMSB or fitted numerical
reference JSON is bundled.**

Upon a calculation requesting a missing reference, the package obtains
the original HTTPS source, verifies pinned SHA-256 checksums, transforms
the source to the runtime representation, and caches it in user data outside
the installed Python package. An unavailable reference can be retried later.

## Original scientific data and unresolved terms

Original reference provider: **WHO Child Growth Standards 2006**.
Official resource: https://www.who.int/tools/child-growth-standards/standards

WHO 2006 includes 420 additional source rows outside the WHO R oracle; review their original website terms.

**Original source access, automated downloading, transformations and
downstream usage rights remain subject to source-specific review.**
Code-only packaging removes the redistribution of numerical coefficient
files by this project but does not grant downstream permissions.

Additional provenance and research evidence are documented in
data/SOURCE_RIGHTS.json, data/SOURCE_LICENSE_MATRIX.json, and the
source manifest. The R_PACKAGE_GPL_LICENSE.txt file covers a separate
R validation implementation; it does not license original scientific data.

This package is not endorsed by WHO Child Growth Standards 2006.
