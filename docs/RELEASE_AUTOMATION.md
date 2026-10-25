# Release workflows and automatic API-diff versioning

## MIT core: automatic, from main

Pushes to the reviewed `main` branch trigger `.github/workflows/release.yml`.
This workflow invokes public code-only CI, compares the new
`api-schema.json` to the schema in the latest GitHub core release,
computes the next semantic version automatically, builds **only**
`pedgrowth`, validates its wheel and sdist, and publishes through
GitHub Actions/PyPI Trusted Publishing. Initial release: `1.0.0`.
Unchanged public API increments the patch/build component; additive
API changes increment minor; changing/removing a public API increments major.
See `scripts/auto_version.py` for the schema comparison contract.

This core release does **not** redistribute WHO, CDC or INTERGROWTH
scientific coefficients, and requires no third-party reference-data approval.
Publishing the entire research Git repository is a **separate rights issue**.

## Scientific provider releases: manual, independent, fail-closed

`.github/workflows/provider-release.yml` accepts one provider per run.
It verifies that exact provider's signed source-rights clearance,
approved metadata and license documents, and builds **only that provider**.
Before publication, it confirms that a matching version of the core is
already available on PyPI. The provider package is tested for package
and scientific-resource integrity, then published using PyPI Trusted
Publishing. A separately named GitHub release records its artifacts.

- WHO 2006/2007 and INTERGROWTH wheels and sdists are *code-only*.
  Reference values are acquired from pinned upstream sources on the
  user's machine, checksum validated, and stored in a user-data cache.
- CDC now follows the verified on-demand CSV-source download path and
  packages **no scientific coefficient files**. Its local data-use and
  transformation terms still require source-specific review.
- The absence of coefficients from a wheel does not automatically grant
  permission to fetch, transform or use upstream content. The provider
  workflow intentionally retains a signed rights/terms gate.

## CI and independent scientific verification

`.github/workflows/ci.yml` supports a public checkout with no private
scientific coefficient snapshots. It runs static analysis and data-free
core tests across supported Python/OS versions, builds/inspects the
MIT-only wheel/sdist and smoke-tests clean installation.

GitHub's public test job installs the `dev` extra, including `types-requests`
for strict mypy analysis of the legacy source-verification script. The
cross-platform workflow explicitly selects the Bash shell for its
scientific-fixture detection, including on Windows runners, rather than
passing Bash syntax to PowerShell.

When the *private research fixtures* are present, CI executes the full
numerical test suite and cross-platform reproducibility probes.
`.github/workflows/official-validation.yml` remains a dedicated,
separately triggered R-based external-validation workflow for scientifically
validated reference publications. Public code-only CI must not be
mistaken for full validation of downloadable scientific providers.
`python scripts/check_public_source.py --git-index` rejects protected
scientific CSV, compiled LMSB, and older reference-derived test datasets
that have inadvertently been staged for public Git publication. The same
script validates a candidate source archive by filename and content policy.
This does not analyze historical commits or replace manual rights review.
`.github/workflows/live-reference-check.yml` separately checks the
pinned WHO and CDC source downloads and converters.

## Repository and PyPI setup still required

The configured publication repository is `https://github.com/erknet/pedgrowth`.
The local development branch is `main`. Before publication, verify that
this repository exists and has a reviewed, protected remote `main` branch;
verify GitHub Actions/OIDC permissions and configure PyPI Trusted Publishers:

- Core: repository `erknet/pedgrowth`, workflow
  `release.yml`, environment `pypi`.
- Each separately cleared provider: same repository, workflow
  `provider-release.yml`, environment `pypi`.

No Git push or PyPI release is performed by these local changes.
Review the **entire Git history and index** for previously committed
third-party reference values before making any repository public.
`.gitignore` protects future additions; it does not erase historical
commits. A new clean history or deliberate history rewrite may be
necessary and must be reviewed independently.
