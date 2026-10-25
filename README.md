# pedgrowth — extensible pediatric growth engine

A monorepo of five **independent Python distributions**, not a single runtime package containing every scientific dataset.

~~~text
packages/
  pedgrowth/                    # MIT calculation engine, contracts, plugin discovery
    pyproject.toml
    src/pedgrowth/
  pedgrowth-data-who2006/       # WHO 2006 tables, reference policy and plan
    pyproject.toml
    src/pedgrowth/data/who2006/
  pedgrowth-data-who2007/       # WHO 2007 tables and plan
    pyproject.toml
    src/pedgrowth/data/who2007/
  pedgrowth-data-cdc/           # CDC tables and clinical/fallback plans
    pyproject.toml
    src/pedgrowth/data/cdc/
  pedgrowth-data-intergrowth/   # INTERGROWTH equations and plan
    pyproject.toml
    src/pedgrowth/data/intergrowth/
tests/                           # Scientific oracles, fixtures, tests
validation/source_data/          # Audited source snapshots, outside runtime
scripts/                         # Builds, checks, versioning, R reproducibility
docs/                            # Usage, extension and licensing documents
~~~

The MIT core contains **no tests, WHO/CDC tables, INTERGROWTH implementations, reference coefficients, or test datasets**. Providers own their tables, selection rules, plans, source metadata, and packaging. Extensions automatically register themselves through Python entry points; the engine never imports provider packages directly.

## Installation

Python 3.11+. The calculation engine has no mandatory third-party dependencies.
Install the core and any separately published scientific providers you need.

**From PyPI (when each distribution is available):**

~~~bash
python -m pip install pedgrowth
python -m pip install pedgrowth-data-who2006
python -m pip install pedgrowth-data-who2007
python -m pip install pedgrowth-data-cdc
python -m pip install pedgrowth-data-intergrowth
~~~

You can also install all the providers at once using
`python -m pip install 'pedgrowth[all]'`, or select `pedgrowth[who]`,
`pedgrowth[cdc]`, `pedgrowth[intergrowth]`, `pedgrowth[numpy]`
or `pedgrowth[pandas]`. Provider dependencies are pinned to the
matching core distribution version; an extension may not be available
on PyPI until its separate code-only release has completed.

**From this monorepo checkout**, use editable installations:

~~~bash
python -m pip install -e './packages/pedgrowth[dev,pandas]'
python -m pip install -e ./packages/pedgrowth-data-who2006
python -m pip install -e ./packages/pedgrowth-data-who2007
python -m pip install -e ./packages/pedgrowth-data-cdc
python -m pip install -e ./packages/pedgrowth-data-intergrowth
python -m pytest -q
~~~

Or build the five independent distributions locally:

~~~bash
python scripts/build_distributions.py --mode local --output-dir .local/split-distributions
python scripts/check_data_distributions.py .local/split-distributions
~~~

All four providers distribute **code and audited source metadata, not
scientific numerical coefficients**. The separate code-only publication checks
do not imply permission to obtain, transform, or use upstream datasets;
their terms are described in each provider's `SOURCE_RIGHTS.md`.

## Automatic reference initialization

WHO 2006 and WHO 2007 provider wheels contain only code and audited source
manifests, **not** protected coefficient tables. On first use of `WhoPlan()`
or `Who2007Plan()`, the corresponding extension downloads the pinned
official WHO spreadsheets, validates their hashes, converts them to LMSB
and caches them outside `site-packages`. INTERGROWTH reconstructs and verifies
its 43 regression parameters from the pinned upstream equation sources.
CDC now also downloads its pinned official CSV references on demand,
without bundling numerical datasets; successful initialization is then offline.

Downloading all installed provider resources in advance is optional:

~~~python
from pedgrowth.data import download_missing_dependencies

download_missing_dependencies()
~~~

This is not necessary for normal calculations; importing the extension or
enumerating registered plans does not download anything. After initialization
the same references are available offline. See
[Automatic reference acquisition](docs/AUTOMATIC_REFERENCE_ACQUISITION.md).

## Discover registered providers and plans

~~~python
from pedgrowth import available_providers, available_plans, create_plan

print(available_providers())  # installed providers only
print(available_plans())      # installed named selection policies
clinical_plan = create_plan("cdc_clinical")
~~~

The installed providers may offer these names: **who**, **who2007**, **cdc**, **cdc_clinical**, **cdc_with_who_fallback**, **who_with_cdc_fallback**, and **intergrowth**. WHO 2007 covers older children and adolescents; it does not replace WHO 2006 below age five.

## Plan-based calculation

~~~python
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator, Sex
from pedgrowth.data.cdc import CdcClinicalPlan

calc = GrowthChartsCalculator(plan=CdcClinicalPlan())
result = calc.calculate(
    indicator="wfa", measurement=12.0, sex=Sex.Male, age=24.0,
    age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
)
print(result.zscore, result.reference_id)
~~~

Another installed extension supplies its own plans:

~~~python
from pedgrowth.data.who2006 import WhoPlan
from pedgrowth.data.intergrowth import IntergrowthPlan

who = GrowthChartsCalculator(plan=WhoPlan())
preterm = GrowthChartsCalculator(plan=IntergrowthPlan())
result = preterm.calculate(
    indicator="wfa", measurement=2.0, sex="M", age=35.0,
    age_definition=AgeDefinition(AgeType.POSTMENSTRUAL, AgeUnit.WEEKS),
)
~~~

## Table-based calculation

~~~python
from pedgrowth.data.cdc.tables import CdcWeightForAge

calc = GrowthChartsCalculator(table=CdcWeightForAge())
result = calc.calculate(
    indicator="wfa", measurement=18.0, sex="M", age=48,
    age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
)
~~~

Direct equation tables also belong to their provider:

~~~python
from pedgrowth.data.intergrowth import IntergrowthPretermWeightForLength

calc = GrowthChartsCalculator(table=IntergrowthPretermWeightForLength())
result = calc.calculate(indicator="wfl", measurement=2.7, sex="F", coordinate=48.0)
~~~

## NumPy and pandas

~~~python
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator
from pedgrowth.data.cdc import CdcClinicalPlan

calculator = GrowthChartsCalculator(plan=CdcClinicalPlan())
scores, reference_ids = calculator.calculate_numpy(
    indicator="wfa", measurements=[10, 12, 14], sexes=["M", "F", "M"],
    ages=[12, 24, 36],
    age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
    errors="coerce",
)
~~~

The built-in WHO, CDC and INTERGROWTH plans **vectorize reference selection** using NumPy eligibility masks, then the engine groups selected LMS tables for vectorized numerical evaluation. A custom scalar-only `ReferencePlan` may still use per-row selection for compatibility. The pandas adapter is **pedgrowth.pandas_integration.calculate_typed_dataframe**.

## Adding a new external reference

Each extension is an ordinary Python project with its own pyproject.toml and source tree. It supplies ReferenceTable subclasses, ReferencePlan factories, immutable source manifests, and an entry-point registration callback:

~~~python
# your_provider/__init__.py
from pedgrowth import ReferenceProvider

def register(registry):
    registry.register(ReferenceProvider(
        name="my-study", family="my-study", module=__name__,
        tables=(MyReferenceTable,),
        plans={"my-study": MyStudyPlan},
    ))
~~~

~~~toml
# pyproject.toml for the new distribution
[project.entry-points."pedgrowth.references"]
my-study = "your_provider:register"
~~~

Automatic entry-point registration also allows `create_plan("cdc_clinical")` without explicitly importing CDC. Direct class imports require the corresponding extension distribution; the core never bundles provider implementations. The core requires **no modifications**. For custom CSV tables, registration, age/coordinate policy hooks and scientific manifests, see [Extending References](docs/EXTENDING_REFERENCES.md).

## Licensing and numerical validation

The core calculation engine is MIT. The WHO/CDC/INTERGROWTH provider distributions are separate artifacts, with file-specific rights evidence and their original scientific sources, and remain blocked for publication until their provider data licenses are resolved. The development monorepo includes research snapshots and needs its own rights review before public release.

See [Licensing and Release](docs/PROVIDER_LICENSE_RELEASE.md), the [40-reference licensing matrix](docs/REFERENCE_LICENSE_MATRIX.json), and [scientific readiness](docs/SCIENTIFIC_READINESS.md). Independent numerical fixtures and R oracle generation stay in tests/, validation/, and scripts/ only.

Research calculations are not certified clinical advice; choose the age definition, population, reference, and measurement protocol deliberately.
