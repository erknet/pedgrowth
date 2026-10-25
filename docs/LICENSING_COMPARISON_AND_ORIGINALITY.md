**Current update:** The project has since adopted MIT for its independently written Python engine and optional, separately licensed numerical reference installation. Historic BSD recommendations in this comparative review are superseded. See OPTIONAL_REFERENCE_SOURCES.md.\n\n# GrowthCharts: comparative licensing and code-origin audit

Reviewed: 17 October 2026. This is a technical code-provenance assessment, not a legal determination that a particular work is or is not derivative. No license or copyright notices were changed by this audit.

## Other scientific growth packages

| Software | Declared code license | Relevance |
| --- | --- | --- |
| [Original pygrowup](https://github.com/ewheeler/pygrowup) | BSD-3-Clause, notice naming UNICEF and contributors | Permissive historical project |
| [pygrowup2](https://github.com/jbaldivieso/pygrowup2) | BSD-3-Clause | Another similar Python implementation |
| [growthcharts on PyPI](https://pypi.org/project/growthcharts/) | MIT | CDC chart Python package, includes CSV files; already controls the PyPI distribution name growthcharts |
| [WHO anthro](https://cran.r-project.org/package=anthro) | GPL-3 | Independent WHO 2006 R reference calculator |
| [WHO anthroplus](https://cran.r-project.org/package=anthroplus) | GPL >= 3 | Independent WHO 2007 R reference calculator |
| [cdcanthro](https://cran.r-project.org/package=cdcanthro) | GPL-3 | Independent CDC/WHO numerical R calculator |
| [gigs](https://docs.ropensci.org/gigs/) | GPL >= 3 | Independent INTERGROWTH/WHO R calculator |
| [childsds](https://cran.r-project.org/package=childsds) | GPL-3 | Pediatric multisource standards |
| [zscorer](https://cran.r-project.org/package=zscorer) | AGPL-3 | Bundles WHO growth data; published distribution does not establish independent WHO permission |

These are software licenses. They are not definitive grants to redistribute all bundled scientific datasets.

## Comparison of the original code and present implementation

Inputs:

- Upstream original: https://github.com/ewheeler/pygrowup at short Git revision 862f1ed.
- 2024 intermediate rewrite: this project's Git HEAD 862eacca0176bcd8722150b531738d4b7762836f, dated 24 July 2024, under the source directory pygrowup_erknet.
- Current GrowthCharts implementation: source directory pedgrowth.

Method: across every pair of Python source files, tokenize Python code and ignore whitespace and comments. Determine the longest identical contiguous sequence. This is a useful exact-code comparison, **not** proof that no reworded or modified expression was copied.

| Comparison | Largest exact contiguous Python token match |
| --- | --- |
| Original pygrowup, five Python files, versus current GrowthCharts, 47 Python files | 7 tokens |
| Original pygrowup versus 2024 project rewrite, 33 Python files | 97 tokens in an old version-information/get_version helper |
| 2024 rewrite versus current GrowthCharts | Repeated table definition and wrapper patterns, up to 49 tokens |

The original upstream uses Observation/Calculator objects, decimal.Decimal and JSON score tables. The present package uses typed reference tables, explicit GrowthPlans, floating-point coefficient evaluation, NumPy integration, and reference data independently obtained from WHO/CDC URLs. The old 97-token version helper was replaced by a new simpler implementation and is not present in the current code.

The substantive source-code continuity identified is from the maintainer's **own 2024 rewrite**, not from the original upstream pygrowup calculator code. Names of standard mathematical concepts, public-domain ideas and independently implemented algorithms are not themselves evidence of copying. Whether any separately licensed documentation, reference compilations, earlier unpublished code or other source was incorporated still deserves a final human review.

## What this means for the BSD-3-Clause license

- If the published source contains **no copyright-protected upstream pygrowup material**, technical inspiration and historical lineage alone do not normally force compliance with the upstream code license. A voluntary, clearly labeled acknowledgement is reasonable.
- If any copyright-protected pygrowup code or prose **is** included, the original BSD-3-Clause notice, conditions and disclaimer must accompany that material. BSD-3-Clause does not require all new code to be licensed under the identical license.
- The root LICENSE is currently **byte-identical** to the original upstream text, giving UNICEF and contributors copyright attribution. That may be misleading as the sole copyright notice for the present, independently authored software. Recommend revising its copyright line to identify the actual owners of the present code, while preserving upstream notices for any retained protected material, if found. Keep an historical credit in AUTHORS and PROVENANCE regardless.
- Do not remove or rewrite the existing license notice based solely on an automated token comparison. The current audit supports an **independent rewrite assessment**, not a legal warranty or formal chain-of-title opinion.

The much larger unresolved permission question is WHO/INTERGROWTH dataset redistribution, addressed in REFERENCE_REUSE_RIGHTS.md. The copyright on Python code and the rights to redistribute statistical tables are distinct.

## R test dependency separation

The dedicated .github/workflows/official-validation.yml workflow installs WHO anthro, anthroplus, and cdcanthro as **validation-only** R dependencies. It downloads unmodified gigs v0.5.2 R source and verifies pinned file hashes before executing the independent numerical test fixtures. The runtime Python dependencies are empty, and no R or GPL R code is bundled in the production wheel. Python project-authored R testing wrappers in a source distribution are not equivalent to bundling third-party GPL source into the runtime. An R package's GPL license does not automatically apply to independently authored Python merely because R was used to test numerical output.

## Important release blocker: the PyPI project name

[PyPI growthcharts](https://pypi.org/project/growthcharts/) was published by another developer in February 2026 (MIT license). As of this review it is not available for a new unrelated uploader. Decision, 17 October 2026: use `pedgrowth` as the PyPI distribution and top-level import; do not install the conflicting `growthcharts` namespace. Both PyPI name endpoints returned HTTP 404; the name is not reserved until registration. The publication repository is `erknet/pedgrowth`; verify its configuration and trusted-publisher setup before publication.

## Recommendations

1. Keep permissive licensing for independently written GrowthCharts code; BSD-3-Clause is suitable, with MIT or Apache-2.0 also possible.
2. Keep factual historical credit for original pygrowup authors, but do not automatically assign them copyright of newly written code. Review chain of authorship and any retained upstream expression before rewriting LICENSE.
3. Keep R implementations exclusively as external test dependencies in GitHub Actions; never copy their GPL program code into Python.
4. Resolve third-party scientific reference rights separately, regardless of what licenses other tools have chosen.
5. Publish under the selected `pedgrowth` distribution name after registration and configuring GitHub/PyPI trusted publishing.

These conclusions are technical and do not substitute for legal advice or permissions from rights holders.

## Updated independent R licensing and new distribution identity

See [R_VALIDATION_LICENSES.md](R_VALIDATION_LICENSES.md) for version-verified GPL-3 licensing and the important distinction between software copyright and numerical results. The selected PyPI distribution and sole shipped Python namespace are pedgrowth. The old growthcharts import is intentionally not included because an unrelated PyPI distribution owns it.

### Namespace-collision correction

Verification of the wheel currently published on PyPI under the separate growthcharts distribution found its own growthcharts/__init__.py and package modules. Therefore, distributing a pedgrowth wheel which ALSO owns the growthcharts import path would create a file/path conflict. The implemented decision is to make both the pip distribution and all importable Python modules pedgrowth-only. The legacy namespace is not distributed, and consumers should update imports when adopting this new, unpublished library.
