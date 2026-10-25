# pedgrowth monorepo: MIT engine and optional reference-source packages

## Repository vs. Python distributions

The **one development repository** contains the independent MIT calculation
engine, the research reference sources, their source-manifest hashes,
provider-specific rights metadata, the independent R validation tools and
scientific tests. Five permanent projects under `packages/` each build their own independent
Python distribution. Source snapshots and validation oracles remain outside
all installable package source trees.

| PyPI distribution | Import namespace | Content | Software/data terms |
| --- | --- | --- | --- |
| `pedgrowth` | `pedgrowth` | Computation API, generic reference contracts, extension discovery | MIT engine; no coefficient files |
| `pedgrowth-data-who2006` | `pedgrowth.data.who2006` | 18 WHO 2006 LMS tables | WHO source-specific rights; clearance pending |
| `pedgrowth-data-who2007` | `pedgrowth.data.who2007` | 6 WHO 2007 LMS tables | WHO source-specific rights; clearance pending |
| `pedgrowth-data-cdc` | `pedgrowth.data.cdc` | 9 CDC 2000/2022 LMS tables | US federal public-domain considerations, attribution and exceptions |
| `pedgrowth-data-intergrowth` | `pedgrowth.data.intergrowth` | 43 INTERGROWTH fitted regression parameters | INTERGROWTH source-specific rights; clearance pending |

Every provider is a separate *pip distribution* and contributes its own
`pedgrowth.data.<provider>` module beneath a shared import namespace. The
core owns and extends both package search paths, including the
`pedgrowth.data` bulk initializer. Extensions must never ship their own
`pedgrowth/__init__.py` or `pedgrowth/data/__init__.py`; consequently no wheel
overwrites the core or another provider. The generic registry discovers the
installed extensions via entry points, and the core reads their checksum-pinned
resources without hard-coded imports. For test and research use, a user-selected
local directory can also supply verified copies of the datasets.

**The repository is not itself under a single MIT license.** MIT applies
to original engine code. Scientific data retain source-specific terms,
including when the files are committed into the same Git repository.

## Original R GPL and source-data provenance

Each provider wheel and sdist now includes its corresponding original
R software GPL license and full GNU GPL v3 text, linked to the R
package source and the official scientific tables or equations.
The independently authored WHO and INTERGROWTH bootstrap modules use the
corresponding GPL expression; the independent CDC bootstrap is MIT.
The numerical values retain their separate provider rights. Only the CDC
wheel and sdist bundle coefficient source CSVs and compiled LMSB files. WHO
2006/2007 and INTERGROWTH wheels and sdists contain no scientific coefficient
values; they acquire and verify original sources on first use. All extensions
retain independently audited provenance and license evidence matrices.
An R program GPL license does not automatically relicense third-party data.

Each provider includes `data/SOURCES.json` (or the INTERGROWTH equation manifest),
`data/SOURCE_RIGHTS.json`, `data/SOURCE_LICENSE_MATRIX.json`, `SOURCE_RIGHTS.md`,
`README.md`, and an independent software `LICENSE`, as well as the referenced
upstream `R_PACKAGE_GPL_LICENSE.txt`. These explain where each value came from,
the role of the R implementation in scientific verification and usage,
and the independently developed conversion and packaging process.

See [full original R license and scientific source audit](REFERENCE_R_PACKAGE_PROVENANCE.md).

## Building the whole repository

From the repository root, with `build`, `setuptools>=77` and `wheel`
installed:

```bash
python scripts/build_distributions.py --mode local
python scripts/check_data_distributions.py .local/split-distributions
python scripts/check_wheel.py .local/split-distributions/pedgrowth-1.0.0-py3-none-any.whl
python scripts/check_sdist.py .local/split-distributions/pedgrowth-1.0.0.tar.gz
python scripts/check_namespace_installations.py .local/split-distributions
```

The default **local** command produces five wheels and five source archives
under `.local/split-distributions/` (which is Git-ignored). All four
provider wheels include a `LOCAL_QA_ONLY.json` marker and accompanying
notices prohibiting public upload under the presently unresolved rights
status. The directory additionally contains a prominent
`NOT_FOR_PUBLIC_DISTRIBUTION.txt` file and a SHA-256 build index.

The builder validates every source against its original downloaded-file
digest, normalized CSV digest and deterministic packed-binary digest.
Original URLs, versions and file hashes live inside each provider's own
scientific `data/SOURCES.json` and `data/SOURCE_LICENSE_MATRIX.json`.
The MIT core wheel and sdist contain **only generic code, contracts,
entry-point discovery and provider initialization coordination**: no source/rights catalogs, numerical tables, R validation
fixtures or INTERGROWTH regression constants. The scientific validation fixtures
remain in the local research checkout, not in the MIT distributions.

## Installing independent local packages

With a local build wheelhouse:

```bash
python -m pip install --no-index --find-links .local/split-distributions "pedgrowth[cdc]"
python -m pip install --no-index --find-links .local/split-distributions "pedgrowth[who]"
python -m pip install --no-index --find-links .local/split-distributions "pedgrowth[intergrowth]"
python -m pip install --no-index --find-links .local/split-distributions "pedgrowth[all]"
```

Extras are convenience dependency selectors; they are not license grants.
These provider projects **have not been registered or released on PyPI**.
Until release clearance is granted, use the local wheelhouse only where
the datasets were lawfully obtained and use is permitted.

Each provider distribution has a version-specific requirement on the
MIT engine, and the core extras specify matching provider versions. For example,
`pip install pedgrowth-data-cdc` (once published) provides
`from pedgrowth.data.cdc import CdcClinicalPlan`; it does **not** expose
`CdcClinicalPlan` directly from `pedgrowth`. The
automatic release version generator updates all four names together.
Pinning intentionally prevents users from silently mixing incompatible
scientific reference datasets after the engine's source hashes change.

The independent `pedgrowth-data-cdc` wheel can be installed alone with
the MIT engine to support explicit CDC calculation plans; WHO 2006 and
WHO 2007 can each be installed independently. The registered WHO plan uses
all installed WHO tables; full coverage from birth through adolescence needs
both provider distributions. INTERGROWTH needs
only its source package.

An alternative is to install your own licensed, normalized data files:

```bash
python -m pedgrowth.references list
python -m pedgrowth.references install cdc --from-dir /path/to/normalized-data --accept-source-terms
```

This secondary loader performs no downloads and verifies the exact pinned
hashes; accepting provider terms is a user acknowledgment, not a grant
of source redistribution rights. The `PEDGROWTH_REFERENCE_DIR` variable
selects an explicit user reference directory and isolates it from the
installed provider packages, making local reference selection reproducible.

## Rights and public release controls

The source-specific license status is recorded in
`validation/source_data/SOURCE_LICENSES.json`. The current provider packages do
**not** assert guessed SPDX license expressions for WHO/INTERGROWTH data.
A published provider wheel can declare its own verified SPDX or
`LicenseRef-...` terms, independently of the MIT engine.

The **publication** build validates selected providers' independent Python
code, audited source metadata, SPDX code license, source-use attribution,
and lack of bundled scientific coefficients:

~~~bash
python scripts/verify_reference_rights.py --enforce-publication --providers cdc
python scripts/build_distributions.py --mode publication --components cdc --output-dir .local/cdc-release
~~~

No signed permission to redistribute *absent* scientific datasets is needed
for this code-only build. Upstream terms for the user's later downloads and
use remain a distinct question; see the provider SOURCE_RIGHTS.md and the
[source-by-source audit](PROVIDER_LICENSE_RELEASE.md).

The separate signed data redistribution check remains available via
`--enforce-data-redistribution` for any future data-inclusive build.
GitHub automatically releases only the MIT core; the provider workflow
is manually dispatched for one provider at a time.

**Making the Git repository public is independently a redistribution of
everything tracked in that repository.** Simply stripping reference
tables from the MIT wheel does not make a public Git repository containing
those tables legally safe. Do not make this research checkout public
unless the rights for the committed scientific datasets and fixtures
are documented. If those rights cannot be established, the public Git
repository will need to exclude the relevant data, or the project
must remain private.

The automatic `release.yml` workflow builds and publishes **only** the
MIT core. Each code-only reference provider is built and published
independently through a manually dispatched `provider-release.yml` job.
Each PyPI project needs its own Trusted Publisher configuration using the
correct workflow file (`release.yml` for the core,
`provider-release.yml` for extensions) and protected `pypi` environment.
Routine CI uploads only the MIT core artifacts; it never publishes
provider distributions. None of these workflows grants rights to upstream
scientific content downloaded on a user's machine.

## Independent scientific validation

WHO 2006/2007 tables were checked against WHO's GPL-licensed
`anthro`/`anthroplus` programs, CDC against `cdcanthro`, and
INTERGROWTH against the external `gigs` R implementation. R programs
are separate test dependencies; none of their protected source code is
linked or vendored into the MIT engine or data-only wheel packaging.

The verified source hashes, cross-version numerical oracles and
source-specific rights evidence are maintained in the same monorepo.
The archived original R packages are not included in any wheel/sdist.

See `REFERENCE_REUSE_RIGHTS.md`,
`WHO_R_COEFFICIENT_RIGHTS_AUDIT.md`, `R_VALIDATION_LICENSES.md`
and `REFERENCE_PUBLICATION_CLEARANCE.example.json`.
