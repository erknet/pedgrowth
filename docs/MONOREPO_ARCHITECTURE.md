# Monorepo package boundaries

This repository is a **workspace**, not an installable Python distribution.
The root has tooling, shared offline validation and metadata; each project under
packages/ has its own installable pyproject.toml.

~~~text
packages/pedgrowth/src/pedgrowth/                  generic engine, interfaces, registry
packages/pedgrowth-data-who2006/src/pedgrowth/data/who2006/   WHO 2006 tables, policy, plan, data
packages/pedgrowth-data-who2007/src/pedgrowth/data/who2007/   WHO 2007 tables, plan, data
packages/pedgrowth-data-cdc/src/pedgrowth/data/cdc/           CDC tables, policy, plans, data
packages/pedgrowth-data-intergrowth/src/pedgrowth/data/intergrowth/  equations, plan, data
tests/                                             test programs + frozen oracles
validation/source_data/                            official source snapshots + rights manifests
scripts/                                           builders, source verification and R oracles
docs/                                              usage, licensing, extensions and architecture
~~~

## Contract

The core owns only generic contracts, execution and the provider-data
initialization coordinator. The core's regular `pedgrowth` and `pedgrowth.data`
packages extend their respective import search paths, allowing independent
distributions to contribute `pedgrowth.data.<provider>` subpackages. The core
exports `download_missing_dependencies()` from `pedgrowth.data`, while extensions
never ship their own `pedgrowth/__init__.py` or `pedgrowth/data/__init__.py`:

- ReferenceTable describes indicator, domain, scalar evaluation, optional provenance and optional age conversion.
- ReferencePlan describes selection and available tables.
- ReferenceRegistry lazily discovers the registered extensions from Python entry points in the pedgrowth.references group.
- `ReferenceCandidate` and `ReferenceBatchCandidate` carry model-agnostic coordinate/measurement adjustments. Providers supply scalar `candidate_policy`/`accept_policy` and NumPy `batch_candidate_policy`/`batch_accept_policy` as needed.
- GrowthPlan is an optional generic ordered selector. WHO/CDC clinical thresholds and conversions are defined by their providers, not by GrowthPlan.
- The generic NumPy selector combines provider-supplied **array masks**, table domains, sex and precedence. It does not call scalar reference selection per observation. LMS evaluation, output grouping and pandas adapters also belong to the core.

Each provider owns its tables, plans, source conversion, optional acquisition
callback, licensing evidence and reproducibility metadata. WHO 2006/2007 and
INTERGROWTH download their scientific data upon first table/plan initialization,
validate hashes and store them in a user cache; CDC follows the same
pattern using original CDC CSV sources. Installing a provider exposes its plans without downloads.
Installing just the MIT core exposes no reference tables. Users can still pass
an arbitrary table or plan directly without any provider distribution.

WHO 2006 and WHO 2007 are independent distributions, though the registered
WHO selection family may use both when both are installed. The CDC extension
provides the clinical cross-provider fallback plan but does not depend on or
install WHO; a clinical policy requiring an absent WHO table fails explicitly.

## No tests inside packages

All scientific oracle generation, R tests, test fixtures and raw audit snapshots
live in repository-level tests/, scripts/ and validation/ directories. The WHO 2006, WHO 2007 and INTERGROWTH wheels **and sdists** contain no
coefficient data. They contain only acquisition code and reviewed manifests.
CDC also distributes code-only with pinned official data acquisition
and binary compilation; private research snapshots remain separate.
Research-only snapshots in the private checkout are excluded from package
builds and ignored for future Git tracking.

The core wheel contains no source-data files, model parameters or test data.
Provider wheels cannot contain a copy of the core or tests. Package integrity
scripts verify these conditions after every native build.

## Local commands

~~~bash
python -m pip install -e './packages/pedgrowth[dev,pandas]'
python -m pip install -e ./packages/pedgrowth-data-who2006 -e ./packages/pedgrowth-data-who2007 \
  -e ./packages/pedgrowth-data-cdc -e ./packages/pedgrowth-data-intergrowth

python -m pytest -q
python -m ruff check packages scripts tests
python -m ruff format --check packages scripts tests
python -m mypy

python scripts/build_distributions.py --mode local --output-dir .local/split-distributions
python scripts/check_wheel.py .local/split-distributions/pedgrowth-1.0.0-py3-none-any.whl
python scripts/check_sdist.py .local/split-distributions/pedgrowth-1.0.0.tar.gz
python scripts/check_data_distributions.py .local/split-distributions
~~~

Each provider may also be installed and tested individually using only its
wheel and the core wheel in an isolated environment. See the project-level
README for plan-based, table-based and third-party registration examples.

## Release and source rights

The automated API diff is generated from **all five** package source trees.
Version injection writes to each package's own pyproject.toml and the core
runtime version; it does not create a Python project at the monorepo root.

The automated `release.yml` workflow publishes only the MIT core. Each
provider can be published separately using `provider-release.yml`, which
verifies its independently declared Python code license, provenance, and strict
code-only wheel/sdist contents. It does **not** bundle third-party reference
coefficients or require a redistribution approval for datasets absent from the
package. Source-specific rights for users' later downloading, transformation,
and use are separately documented and not automatically granted.

A future distribution that bundles scientific coefficients requires a distinct
signed data-redistribution review. The private research monorepo and its Git
history also require an independent source-data audit before publication.
Local QA artifacts are not evidence of a completed PyPI release.
