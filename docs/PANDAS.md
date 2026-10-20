# Pandas integration

Install `pip install 'pedgrowth[pandas]'` once the independent source-data distributions you need are available (or install verified local reference files). Pandas and NumPy are optional; installing the `[pandas]` extra installs both. The scalar library has zero required third-party dependencies.

```python
import pandas as pd

from pedgrowth import GrowthChartsCalculator
from pedgrowth.pandas_integration import calculate_dataframe

frame = pd.DataFrame({
    "weight_kg": [10.0, 12.0, 14.0],
    "age_months": [12.0, 24.0, 36.0],
    "sex": ["M", "F", "M"],
})

result = calculate_dataframe(
    frame,
    GrowthChartsCalculator(standard='who'),
    indicator='wfa', measurement='weight_kg', index='age_months', sex='sex',
    output='wfa_z', errors='coerce',
)
```

The first adapter supports the **legacy calculator without an explicit plan** and requires an installed WHO provider covering the data. For a plan or direct table, use the typed adapter, which additionally records the selected reference for every observation. This clinical example needs **`pedgrowth-data-cdc` and `pedgrowth-data-who2006`** because the plan selects WHO below 24 months:

```python
from pedgrowth import AgeDefinition, AgeType, AgeUnit, GrowthChartsCalculator
from pedgrowth.data.cdc import CdcClinicalPlan
from pedgrowth.pandas_integration import calculate_typed_dataframe

results = calculate_typed_dataframe(
    frame,
    GrowthChartsCalculator(plan=CdcClinicalPlan()),
    indicator="wfa", measurement="weight_kg", sex="sex",
    age="age_months",
    age_definition=AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS),
    output="zscore", reference_output="reference_id", errors="coerce",
)
```

Both adapters return a new DataFrame and retain row order and index. With `errors='raise'` (the default), invalid data result in an exception. With `errors='coerce'`, invalid rows receive NaN, and in the typed adapter an empty reference ID. Built-in WHO, CDC and INTERGROWTH plans perform NumPy-vectorized reference selection. Custom scalar-only third-party plans may select per row; LMS evaluation remains vectorized. Invalid original inputs remain in the returned frame, making exclusions auditable. Do not silently interpret NaNs as normal or absent growth deficits.
