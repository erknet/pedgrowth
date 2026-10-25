# Provenance and attribution

pedgrowth is a substantially rewritten WHO/CDC growth-reference calculation library.
Its historical lineage includes [ewheeler/pygrowup](https://github.com/ewheeler/pygrowup).
The current implementation is maintained by ERKNet.

Original contributors included Evan Wheeler, M. Jackson Wilkinson, and Jon Baldivieso.
Historical attribution is retained without claiming they authored the rewritten implementation.
The independently authored current Python engine is MIT licensed. An audit
against the original pygrowup release found no substantial verbatim source
reuse in the current engine. Historical contributors are acknowledged here,
but the MIT license does not erase the original BSD-3-Clause obligations if
a future human review finds protected upstream material.
WHO and CDC reference data are third-party scientific sources with their own provenance and usage conditions.

## Release and hosting
The publication repository is `erknet/pedgrowth`. Release workflows
target the `main` branch. Confirm that the reviewed public-source tree is
present on a protected remote `main` branch before enabling automatic
GitHub Actions publishing. No public pedgrowth release was performed by
this workspace.

## Third-party scientific reference terms

The normative scientific reference data and regression equations are
independently sourced and have separate license/attribution terms. See
`THIRD_PARTY_NOTICES.md` and `docs/REFERENCE_REUSE_RIGHTS.json` for
the complete per-source URL/hash audit and rights review. The MIT
engine license does not extend third-party permissions to redistribution.
**Public publication of bundled scientific values remains gated pending
source-specific rights clearance.** The separate MIT core is code-only;
provider extensions must still observe applicable upstream acquisition and
use terms.
