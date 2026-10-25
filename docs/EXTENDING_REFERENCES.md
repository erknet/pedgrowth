# Extending pedgrowth: external tables, mathematical models, and plans

The calculator is an **execution engine**. Reference tables implement **numeric evaluation**. Plans implement **selection policy**. These are independent extension points; extending either does not require editing `GrowthChartsCalculator`.

| Component | Interface | Responsibility |
| --- | --- | --- |
| Engine | `GrowthChartsCalculator` | Input validation, scalar/NumPy/Pandas execution, reference identity, errors |
| Reference table | `ReferenceTable` | Indicator, supported sex/coordinate range, z-score calculation |
| Selection plan | `ReferencePlan` | Select a table and adjusted coordinate from clinical/research policy |
| LMS table | `GrowthTable` | Validated LMS storage and default z-score algorithm |
| External data | `TableDefinition` + `CsvGrowthTable` | Add an LMS table from a local CSV without custom Python code |

The calculation engine, generic selection algorithm and reference contracts live in `packages/pedgrowth/src/pedgrowth/`. Concrete WHO/CDC/INTERGROWTH tables, scientific selection policies and registered plans are implemented **only** by their corresponding independent extension packages under `packages/pedgrowth-data-*/src/`. The engine does not import or re-export provider-specific implementations.

## 1. Add an external LMS table — data only

```python
from pathlib import Path
from pedgrowth import (
    AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator,
    CsvGrowthTable, TableDefinition, TableType, Sex,
)

definition = TableDefinition(
    name="study_wfa_boys_v1",
    indicator=TableType.WeightForAge,
    source=Path("references/study_wfa_boys.csv"),
    sex=Sex.Male,
    standard_name="research cohort",
    reference_version="2026",
    source_url="https://example.org/your-published-reference",
)

table = CsvGrowthTable(definition)
calculator = GrowthChartsCalculator(table=table)
result = calculator.calculate(
    indicator="wfa",
    measurement=10.0,
    sex="M",
    age=18,
    age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
)
```

The source URL above is an **example placeholder**, not an actual dataset URL.

Normalized CSV columns: `sex,index,l,m,s,sigma`; extended CDC-style BMI adds `p95`. For sex-specific files with `sex=Sex.Male` or `Sex.Female`, the CSV's `sex` field is blank. For a shared `sex=None` file, both `M` and `F` partitions must be present with matching coordinate indices. `index` is age in months or length/height in cm. File contents are validated strictly, and their SHA-256 is retained as table provenance.

For legacy reference selection (without an explicit plan), use `additional_tables=[definition]` to give an external table precedence over any installed reference providers. To replace an existing named table in a legacy calculator, use `table_overrides={"existing_table_name": Path("new.csv")}`.

**Do not modify installed reference data in place.** Build distinct versioned source tables and keep their origin and numerical validation records.

## 2. Implement an entirely different mathematical model

Subclass the model-independent `ReferenceTable`. You must define the indicator and domain as well as the scalar evaluator. For example, this deliberately simple **synthetic demonstration**, not a medically valid reference, has z-score `(measurement - 10) / 2`:

```python
from pedgrowth import GrowthChartsCalculator, Sex, TableType
from pedgrowth.tables.table import ReferenceTable
from pedgrowth.exceptions import DataNotFoundError, InvalidMeasurement

class DemonstrationTable(ReferenceTable):
    def get_file_name(self) -> str:
        return "demonstration_wfa"

    def get_table_type(self) -> TableType:
        return TableType.WeightForAge

    def get_min_range(self) -> float:
        return 0.0

    def get_max_range(self) -> float:
        return 24.0

    def calculate_zscore(self, index_value, measurement, sex=None, interpolation="nearest"):
        if not 0 <= index_value <= 24:
            raise DataNotFoundError("Outside demonstration domain")
        if measurement <= 0:
            raise InvalidMeasurement("Measurement must be positive")
        return (measurement - 10.0) / 2.0

calculator = GrowthChartsCalculator(table=DemonstrationTable())
```

The example is for interface demonstration only. A real reference model must specify and validate its units, sex coverage, published domain, tails, and scientific provenance. A direct table uses `table=` rather than a `plan=`; it never falls back to another table.

## 3. Add your own selection plan — no calculator changes

A plan must expose two methods: `resolve(...)`, which returns `ResolvedReference(table, coordinate, measurement_offset)`, and `tables()`, which returns all possible candidate tables for provenance reporting. The `ReferencePlan` Protocol is structural: your class **does not need to inherit** a built-in plan.

```python
from pedgrowth import (
    AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator, Indicator,
    ReferencePlan, ResolvedReference, Sex,
)
from pedgrowth.exceptions import DataNotFoundError
from pedgrowth.tables.table import ReferenceTable

class StudyPlan:
    def __init__(self, table: ReferenceTable) -> None:
        self._table = table

    def tables(self) -> tuple[ReferenceTable, ...]:
        return (self._table,)

    def resolve(
        self, *,
        indicator: Indicator | str,
        sex: Sex | str,
        age: float | None = None,
        age_definition: AgeDefinition | None = None,
        coordinate: float | None = None,
    ) -> ResolvedReference:
        if Indicator(indicator) is not Indicator.WEIGHT_FOR_AGE:
            raise DataNotFoundError("Study plan supports only weight-for-age")
        if age_definition != AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS):
            raise ValueError("Study plan requires chronological months")
        if age is None or not self._table.get_min_range() <= age <= self._table.get_max_range():
            raise DataNotFoundError("Age outside study reference")
        if self._table.get_table_sex() not in (None, Sex(sex)):
            raise DataNotFoundError("Sex outside study reference")
        return ResolvedReference(self._table, age)

# Reuse DemonstrationTable from example 2 above. This example is synthetic.
policy: ReferencePlan = StudyPlan(DemonstrationTable())
calculator = GrowthChartsCalculator(plan=policy)
score = calculator.zscore(
    indicator="wfa", measurement=10.0, sex=Sex.Male, age=18,
    age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
)
```

For an ordinary policy with multiple candidate tables, return all candidates from `tables()` and choose deterministically inside `resolve()`. This supports custom age boundaries, study/cohort restrictions, alternate fallback order, and model-specific use without altering the core engine. No plan should silently reinterpret chronological, corrected, gestational, or postmenstrual ages.

Typed NumPy calls on the bundled WHO, CDC and INTERGROWTH plans perform **vectorized reference selection**, using array eligibility masks for ages, measurement positions, sexes, reference domains and fallback precedence. The engine subsequently groups selected LMS tables for vectorized numerical evaluation. A third-party `GrowthPlan` using custom scalar eligibility hooks must also supply `batch_candidate_policy`/`batch_accept_policy` to support this vectorized path; generic tables without special policy hooks are already vectorized. A separately implemented custom `ReferencePlan` may remain scalar-only and then uses per-row selection for compatibility. Non-LMS equation evaluators may likewise remain scalar even though reference selection itself is vectorized.

## 4. Reference provenance, licensing and tests

Every source reference should document its provider, revision, data license, original URL, SHA-256, numeric transformations and independent validation. Official provider data and any R software used as a validation oracle can have **different licenses**; an R package's GPL declaration is not necessarily permission to redistribute the originating provider's dataset.

To ship a separate provider distribution, model it after `pedgrowth-data-*` rather than adding coefficients to the MIT core. Each provider project owns its scientific manifests and source-specific rights documentation; the monorepo keeps validation scripts and frozen oracle fixtures outside the installable packages. Local QA packages are explicitly marked as not publishable until rights review is complete.

Add tests comparing your scalar reference against trusted external numeric oracles, boundary/invalid cases, reference selection, and (if applicable) NumPy/Pandas parity. Consult [numerical verification](SCIENTIFIC_READINESS.md), [source licensing](REFERENCE_R_PACKAGE_PROVENANCE.md) and [distribution structure](OPTIONAL_REFERENCE_SOURCES.md).


## Vectorized provider policy hooks

A provider that supplies a custom scalar candidate_policy or accept_policy must
also register the matching batch_candidate_policy or batch_accept_policy for
NumPy selection. Batch candidates return ReferenceBatchCandidate records with
scalar or array-valued coordinate and measurement offsets. Batch acceptance
returns Boolean eligibility arrays. A plan can additionally expose
_batch_family_masks for provider-specific age boundaries.

The generic GrowthPlan performs WHO/CDC selection with NumPy masks over table
type, sex, age, eligibility, bounds and fallback precedence; there is no
per-observation scalar selection call. The INTERGROWTH plan has its own
vectorized postmenstrual-age selector. The final result objects are assembled
per selected observation, and a custom structural ReferencePlan that does not
implement resolve_numpy still has scalar fallback for compatibility.



## Shared import namespace (independent wheels)

Built-in providers and optional third-party extensions can contribute their
modules beneath the shared pedgrowth.data namespace without owning or modifying
the pedgrowth core package. Each extension distribution must place its code at
src/pedgrowth/data/<provider>/, without shipping a pedgrowth/__init__.py or
pedgrowth/data/__init__.py. The core owns both regular package initializers,
including pedgrowth.data.download_missing_dependencies(), and extends their
search paths to discover independently installed provider subpackages.

For example, an independent project providing a my_study reference:

~~~text
my-growth-reference/
  pyproject.toml
  src/pedgrowth/data/my_study/
    __init__.py
    plans.py
    tables/
    data/
~~~

~~~toml
[project.entry-points."pedgrowth.references"]
my_study = "pedgrowth.data.my_study:register"

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
include = ["pedgrowth.data.my_study*"]
~~~

It is then available with either an explicit import:

~~~python
from pedgrowth.data.my_study import MyStudyPlan
~~~

or lazily through an already-installed entry point:

~~~python
from pedgrowth import create_plan

plan = create_plan("my_study")
~~~

Module imports and automatic registration are independent: entry points
register all installed providers on demand. Distribution names stay separately
installable by pip; wheels may retain normalized filenames such as
pedgrowth_data_cdc-1.0.0-py3-none-any.whl, which does not create an import alias.
Avoid installing any extension that ships its own pedgrowth/__init__.py since
that would conflict with the core.


## Provider-specific automatic reference initialization

A provider can optionally pass `initialize_data=callable` when registering
its `ReferenceProvider`. The callback checks bundled and cached verified
resources, downloads and compiles only missing resources, and returns an
integer count. The core never embeds scientific source URLs or data formats.
Registration and imports are side-effect free; table use triggers lazy
acquisition. The optional `from pedgrowth.data import
download_missing_dependencies` initializes every registered provider.

The user cache is outside the package installation, enabling read-only
installations and future provider wheels that include licensed data (which
skip downloading). See [reference acquisition](AUTOMATIC_REFERENCE_ACQUISITION.md).
