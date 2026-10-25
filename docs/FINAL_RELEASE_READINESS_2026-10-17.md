# pedgrowth — historical scientific validation snapshot (17 October 2026)

**Historical audit:** The test counts and results below describe earlier audit runs and are preserved for provenance. They are **not** claims about the current monorepo or its latest test results. For the current five-distribution structure, import conventions, build commands and publication requirements, see [the monorepo architecture](MONOREPO_ARCHITECTURE.md), [the README](../README.md), and [source-specific publication review](PROVIDER_LICENSE_RELEASE.md). The current example imports provider plans from `pedgrowth.data.<provider>`, never directly from the core.

**Verdict: Research numerical-validation gates pass locally for the 40 implemented reference tables; public distribution and unrestricted clinical usage are NOT yet approved.**

## Executed validation and results

| Gate | Result | Reproducible evidence |
| --- | --- | --- |
| Unit/regression/scientific validation | Archived October 17 Linux logs: **1,230 passed** for each of Python 3.11, 3.12, 3.13 and 3.14. After the October 19 extension and documentation changes: **1,257 passed** on Python 3.14.7 (Linux); on 3.11–3.13, **1,256 passed and 1 packaging test skipped** per version because those local environments lack the `build` dependency. | `.local/final-py311-tests.log`, `...312...`, `...313...`, `...314...`; October 19 direct test run |
| Per-reference independent numerical validation | WHO 24/24, CDC 9/9, INTERGROWTH 7/7 | `tests/fixtures/who_r`, `official_percentiles`, `intergrowth` |
| Continuous INTERGROWTH numerical agreement | 4,970/4,970 original, hash-pinned `gigs` v0.5.2 R outputs | `tests/fixtures/intergrowth/continuous_manifest.json` |
| Clinical worked and synthetic examples | 42 cases, 5 from CDC published examples, 37 independent WHO/CDC R-vetted synthetic cases; 44 acceptance tests | `tests/test_clinical_vignettes.py`, `tests/fixtures/clinical_cases_manifest.json` |
| Extreme-value safeguards | 88 stress tests; explicit InvalidMeasurement instead of raw LMS OverflowError; CDC stable survival tail | `tests/test_extreme_measurements.py` |
| Reference plan-selection specification | 68 independent expected plan decisions, extensive boundary and scalar/vector tests | `docs/GROWTH_PLAN_POLICY_AUDIT.md` |
| Local cross-interpreter reproducibility | 4 Linux interpreters, 162 probes per interpreter, maximum difference **0.0** | `scripts/reproducibility_probe.py`, `scripts/compare_reproducibility.py` |
| Cross-OS execution | CI configured (12 combinations: Python 3.11–3.14 × Linux/macOS/Windows), **NOT YET RUN** | `.github/workflows/ci.yml` |
| Source authenticity (live) | 33/33 WHO and CDC downloads match pinned SHA-256 and exact normalized coefficients | `.local/official-live-audit.log` |
| Rights metadata coverage | 33/33 WHO/CDC source-specific records + seven INTERGROWTH equation models | `docs/REFERENCE_REUSE_RIGHTS.json` |
| Historical data-redistribution approval | **BLOCKED** for *bundled numerical datasets* pending human rights review | The current code-only provider workflow uses a separate gate; see `PROVIDER_LICENSE_RELEASE.md` |
| Dependency security | `pip-audit --local`: no known vulnerabilities at audit date | Independent local scan |
| Static analysis | Ruff and formatting clean; strict mypy clean | Python CI commands |
| Build and artifact integrity | MIT-only wheel/sdist built; no WHO/CDC tables or INTERGROWTH fitted coefficients included; source license manifest and notices included | `scripts/check_wheel.py`, `scripts/verify_release_version.py` |
| Standalone pure-Python installation | Isolated Python 3.11 imports data-free MIT wheel; separately installed sources restore WHO/CDC/INTERGROWTH without NumPy/SciPy/Pandas | Wheel import smoke test |
| Historical code statement coverage | 89% as measured by pytest-cov, including source-only legacy test module not imported by pytest | `.local/coverage.json` |

**Licensing and source originality:** See [the comparative licensing audit](LICENSING_COMPARISON_AND_ORIGINALITY.md). The chosen distribution is pedgrowth. PyPI endpoints returned 404 on review; the name remains unreserved until registration. The unrelated growthcharts Python import is intentionally not provided, avoiding installation conflicts. The original-code provenance and third-party data rights are independent legal questions.

## Legitimate remaining blockers (not automatable certifications)

1. Run the new GitHub CI matrix and independent WHO/CDC/INTERGROWTH/clinical R workflows on actual GitHub-hosted Windows/macOS/Linux runners. The local cross-interpreter result proves neither Windows nor macOS compatibility.
2. For any future package **bundling scientific numerical datasets**, obtain source-specific redistribution clearance or qualified counsel's supported determination. Current code-only provider wheels and sdists are independently validated, but upstream acquisition and use terms still require user-specific review; see `PROVIDER_LICENSE_RELEASE.md`.
3. Clinically approve the project's **intended-use definition** and cohort-specific reference choices: preterm/gestational age, corrected age, height versus length protocols, WHO/CDC age transitions and disease-specific interpretation. No numerical test or simulated case constitutes a clinical outcome validation study.
4. If the project intends to **support fetal or full-term newborn INTERGROWTH** in addition to the seven currently implemented models, that is new scientific/model development, not a missing validation of the current 40-table scope.
5. Confirm project GitHub URL, protected release environment, trusted publishing settings and explicit release reviewer approval. No code was pushed, tagged or published during this audit.

## Current monorepo verification commands

Run from the repository root after installing the five projects in editable
mode as shown in the [README](../README.md):

```bash
python -m pytest -q
python -m pytest -q --cov=pedgrowth --cov-report=term
python -m ruff check packages tests scripts
python -m ruff format --check packages tests scripts
python -m mypy
python scripts/refresh_data.py --check
python scripts/verify_reference_rights.py
python scripts/build_distributions.py --mode local --output-dir .local/split-distributions
python scripts/check_wheel.py .local/split-distributions/pedgrowth-1.0.0-py3-none-any.whl
python scripts/check_sdist.py .local/split-distributions/pedgrowth-1.0.0.tar.gz
python scripts/check_data_distributions.py .local/split-distributions
python scripts/check_namespace_installations.py .local/split-distributions
python scripts/verify_release_version.py 1.0.0 --dist .local/split-distributions
```

`python scripts/verify_reference_rights.py --enforce-publication` remains a
**deliberate failure** until the independent scientific-data rights have been
reviewed and signed. Hosted cross-platform and external R workflows remain
separate verification requirements.


All validation data used for acceptance are independently obtained or explicitly labeled synthetic values evaluated by external R reference packages. Documentation of source provenance and limitations is in `SCIENTIFIC_READINESS.md`, `REFERENCE_REUSE_RIGHTS.md`, `GROWTH_PLAN_POLICY_AUDIT.md`, and root-level `THIRD_PARTY_NOTICES.md`.

## Distribution and R validation license addendum

The distribution and new top-level import are pedgrowth, while the unrelated growthcharts Python namespace is not included. Repository erknet/pedgrowth must be configured and its main branch reviewed before publishing. All four R validators are external GPL-licensed CI-only programs; see R_VALIDATION_LICENSES.md. No R code or interpreter is a Python runtime dependency.

## WHO-authored R reference-data license evidence

WHO is copyright holder of anthro and anthroplus, whose GPL distributions include reference LMS tables. An independent per-table comparison shows 28,228 identical WHO LMS coefficients across 24 tables, zero mismatches and 420 additional source rows beyond the official R packages' age domain. These results improve the licensed-data provenance argument but do not lift the publication rights gate. See [WHO_R_COEFFICIENT_RIGHTS_AUDIT.md](WHO_R_COEFFICIENT_RIGHTS_AUDIT.md).

## MIT-only core and optional-source architecture (new)

The Python engine now uses MIT (not BSD-3-Clause). Wheel and sdist
exclude all scientific source coefficient files; even INTERGROWTH's 43
fitted numerical constants are separate optional data. Individual
provider rights statuses are recorded in
validation/source_data/SOURCE_LICENSES.json. Separate source installation uses
pinned reference hashes and a user acknowledgement flag that conveys
no new copyright permission. Locally supplied files are required until
provider-specific data distributions have been approved and published.

The archived October 17 suite logs record 1,230 passing tests on each of Python 3.11, 3.12, 3.13 and 3.14. The October 19 current-worktree suite passed 1,257 tests on Python 3.14.7; on Python 3.11, 3.12 and 3.13 the updated suite passed 1,256 tests and skipped the optional wheel-build test once in each environment (missing local `build`). The wheel-build and distribution checks passed separately on Python 3.14.
162 reference probes from the archived audit show zero cross-version numerical drift. The
code-only wheel and sdist contain no dataset coefficients and the
isolated-wheel smoke test confirms optional installed sources restore
WHO, CDC and INTERGROWTH calculations.

**The development Git repository still contains audited scientific
source CSV snapshots and numeric fixtures used for testing.** The
MIT-only PyPI distributions are free of those tables, but publishing
the Git repository itself still requires a separate rights check or
removal of all tracked/staged third-party source snapshots. The release
workflow retains a fail-closed gate. Actual hosted OS CI remains
unexecuted. See OPTIONAL_REFERENCE_SOURCES.md.
