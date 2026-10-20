# pedgrowth — historical release review (17 October 2026)

**Archived audit snapshot:** This page records the decisions made in the earlier flat-package implementation. For the current five independent package projects and imports such as `from pedgrowth.data.cdc import CdcClinicalPlan`, see [MONOREPO_ARCHITECTURE.md](MONOREPO_ARCHITECTURE.md) and [the current README](../README.md). Statements below about legacy package layouts and outstanding feature suggestions should not be treated as current implementation status.

Reviewed: 2026-10-17. **This is not clinical certification.**
Read SCIENTIFIC_READINESS.md for the expanded independent R validation and
outstanding clinical sign-off; the older 108-case matrix is not the full evidence.

## Completed and locally validated

- **Official reference coverage:** 33 datasets (WHO 2006/2007, CDC 2000/2022); original official source SHA-256 and normalized reference data checked against upstream URLs.
- **2022 CDC Extended BMI:** `p95` now read directly from the official P95 column, not derived from rounded LMS. For sub-month interpolation, CDC's published sex-specific quadratic age regressions are used for sigma and P95 is linearly interpolated.
- **Explicit calculation policy:** `standard=who|cdc|who_then_cdc|cdc_then_who`, `interpolation=nearest|linear`, and typed `MeasurementPosition`. Defaults retain prior behavior and legacy parameters.
- **Numerical tests:** frozen 0.9.4 regression fixtures for unaffected calculations, published WHO AnthroPlus/CDC worked examples, interpolated CDC sigma checks, vector/scalar parity, age boundaries and reference transitions.
- **Fast data model:** deterministic non-executable float64 binary LMS format (v2) with optional CDC P95; Normalized editable CSV source accompanies compiled LMS data in each WHO/CDC provider wheel and source distribution under the current monorepo model. NumPy batch arrays cached after first use.
- **Runtime hygiene:** strictly typed mypy, Ruff security/bugbear/import checks, offline scalar without third-party dependencies, no pickle/marshal/eval or source-data execution.
- **CI:** 4 Python versions (3.11–3.14), strict types, automated tests, offline hash integrity, security dependency auditing, clean wheel checks.
- **Release process:** immutable GitHub Action commit SHAs; Dependabot; protected PyPI environment; tag-version verification; OIDC publication with signed attestations; no permanent PyPI token.
- **External numerical test:** optional/local WHO `anthroplus` and CDC `cdcanthro` R comparison via `scripts/export_official.R` and `scripts/validate_official.py`. The independent R workflow is a **mandatory tag-release gate**. Local run on October 16, 2026: 108/108 comparisons passed; max absolute z difference 0.0165135.

## Outstanding before publishing

1. **Push this source to GitHub and run its actual GitHub workflows.** Local checks do not establish that cloud runners, R package installation, or OIDC publishing prerequisites work.
2. **Review the independent R validation output.** R 4.5 has now been installed **inside this project workspace** and the external R comparison executed: 108/108 passed, maximum absolute z error 0.0165135 (threshold 0.03). GitHub CI still must run independently on its cloud runner.
3. **Review official scientific decisions:** nearest-row default versus linear interpolation; fixed 30.4375-day WHO day-to-month conversion; age boundaries, WHO-versus-CDC reference population, standing/recumbent length corrections, and extremely high or low z-scores. The release gate tolerates up to 0.03 absolute z-score deviation; an expert should review each discrepancy rather than treating the threshold as clinical equivalence.
4. **Review data-redistribution permissions** separately for WHO and CDC source tables; the MIT code license does not automatically grant dataset reuse rights.
5. **Configure GitHub's protected `pypi` environment** and register the matching trusted publisher in PyPI project settings. Configure required reviewers to prevent unreviewed tag publication.
6. **Tag only after reviewing release artifacts and CI reports.** No actual PyPI or GitHub publication has occurred in this workspace.

## Future optional enhancements (not release-blocking)

- Support configurable missing-data masks for heterogeneous vector batches. Currently invalid values cause a clear exception instead of silent partially populated arrays.
- Add a clinically designed automatic WHO-to-CDC transition mode (separate from the current four explicit registry preferences).
- Add strict independent end-to-end comparisons against WHO/CDC official SAS and/or AnthroPlus across all supplementary measures, not only BMI/height/weight; consider automatic chart-based plausibility flags as an *optional* distinct API.
- Test across additional architectures and benchmark heterogeneous patient cohorts. Scalar execution remains dependency-free; batch uses NumPy/SciPy C-backed vectorization, not an in-house compiled extension.

## Follow-up: optional array backend and table extensibility

- `pip install pedgrowth[numpy]` installs only NumPy; SciPy is a separate optional extra and the `[vector]` alias remains compatible.
- Public calculation methods have scalar and ndarray type overloads and dispatch only when array-like input is passed; non-array calculations do not import NumPy.
- CSV-backed custom references can be registered through `TableDefinition`/`CsvGrowthTable` and `GrowthChartsCalculator(additional_tables=[...])` without modifying the bundled registry.
- The existing `GrowthTable` subclass interface remains available for trusted code defining new algorithms. A brand-new indicator requires explicit scientific/type/unit support rather than using arbitrary strings.
- R was installed inside `.local/r`; it is intentionally excluded from releases and the wheel.
