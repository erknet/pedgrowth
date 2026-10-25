# Typed growth-reference API

The numeric age value is separate from its AgeDefinition (AgeType and AgeUnit). **Install an optional provider distribution before importing its plan:** for example `pedgrowth-data-cdc` supplies `pedgrowth.data.cdc`, while `pedgrowth` itself supplies only the generic engine.
Indicator, Sex, AgeType and AgeUnit are StrEnum types. A plan resolves one
reference for one indicator; direct tables bypass plans.

**Modules and extension contracts:** `packages/pedgrowth/src/pedgrowth/architecture.py` defines `ReferencePlan`
(the structural plan Protocol), typed ages and `ResolvedReference`;
`packages/pedgrowth/src/pedgrowth/plans.py` implements provider-neutral ordered selection; WHO/CDC/INTERGROWTH implementations and selection policies live in the independent provider packages;
`packages/pedgrowth/src/pedgrowth/tables/table.py` defines `ReferenceTable` and LMS `GrowthTable`;
`packages/pedgrowth/src/pedgrowth/pygrowup.py` supplies the model-independent execution-facing
`GrowthChartsCalculator`. Custom plans implement `resolve(...)` and `tables()`;
custom models implement `ReferenceTable.calculate_zscore(...)` and can supply
`get_provenance()`. The engine does not need to know a custom plan subclass.
See [the extension guide](EXTENDING_REFERENCES.md).

## Predefined postnatal plans

These **plans belong to optional provider distributions**, not the core:
`WhoPlan` is imported from `pedgrowth.data.who2006`, `Who2007Plan` from
`pedgrowth.data.who2007`, CDC plans from `pedgrowth.data.cdc`, and
`IntergrowthPlan` from `pedgrowth.data.intergrowth`. Installing a provider
also registers its named plans for use with `pedgrowth.create_plan()`.


- WhoPlan: WHO only.
- CdcPlan: CDC only.
- CdcWithWhoFallbackPlan: CDC then WHO if no eligible table exists.
- WhoWithCdcFallbackPlan: WHO then CDC if no eligible table exists.
- CdcClinicalPlan: WHO below 24 months and CDC from 24 months up to but
  not including 240 months. BMI-for-age is not offered under 24 months.
  Clinical selection additionally applies 0.7 cm height/length measurement
  adjustments when reference and measurement position differ; it requires
  chronological age for length-based indicators.
- IntergrowthPlan: INTERGROWTH preterm postnatal only; 27–64 postmenstrual
  weeks required for every indicator, **including WFL**. Direct WFL equation
  tables can still be evaluated independently at a length coordinate.

## Example

    from pedgrowth import (
        AgeDefinition, AgeType, AgeUnit,
        GrowthChartsCalculator, Indicator, Sex,
    )
    from pedgrowth.data.cdc import CdcClinicalPlan
    calculator = GrowthChartsCalculator(plan=CdcClinicalPlan())
    result = calculator.calculate(
        indicator=Indicator.WEIGHT_FOR_AGE, measurement=12.0,
        age=24.0,
        age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
        sex=Sex.Male,
    )
    print(result.zscore, result.reference_id)

The typed NumPy API is calculate_numpy(), returning scores and reference IDs.
The Pandas adapter is calculate_typed_dataframe() in pandas_integration.
These remain optional dependencies. Legacy convenience methods intentionally
reject plan/table-configured calculators rather than silently using a wrong
reference.

## Known limitations

- Built-in WHO, CDC and INTERGROWTH plans select references using NumPy eligibility masks. Custom scalar-only `ReferencePlan` implementations select per row; non-LMS equations may evaluate individual measurements using their scalar contract.
- The model-independent ReferenceTable base supports both equation-backed
  INTERGROWTH references and coefficient-backed GrowthTable (LMSTable alias).
  The historical GrowthTable name remains LMS-based for extension compatibility.
- Only the previously supported INTERGROWTH preterm postnatal and very-preterm
  birth equations are available. Fetal and other newborn datasets are not yet
  implemented or independently validated.
- The CDC clinical plan covers the reference transition and standard
  length-versus-stature adjustment; it does not implement prematurity
  corrections, condition-specific screening or all clinical reference policies.
- Month conversion uses 30.4375 days. For exact chronological age from dates,
  provide age in days with the documented conversion convention.
- Python 3.11+ is now required for stdlib StrEnum.
