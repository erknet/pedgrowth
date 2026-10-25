"""Reproducibility metadata and optional Pandas adapter tests."""

from __future__ import annotations

import pytest
from pedgrowth import GrowthChartsCalculator, bundled_references
from pedgrowth.exceptions import DataNotFoundError


def test_bundled_provenance() -> None:
    calculator = GrowthChartsCalculator()
    selected = calculator.reference_for("wfa", 12.0, "M")
    assert selected.name.startswith("who_")
    assert selected.standard == "WHO"
    assert len(selected.data_sha256) == 64
    assert selected == bundled_references()[selected.name]
    assert calculator.available_references()
    with pytest.raises(DataNotFoundError):
        calculator.reference_for("wfa", 10000, "M")


def test_dataframe_adapter() -> None:
    pd = pytest.importorskip("pandas")
    from pedgrowth.pandas_integration import calculate_dataframe

    frame = pd.DataFrame({"mass": [10.4, 12.0], "age": [22.45, 30.0], "sex": ["M", "F"]}, index=[4, 9])
    result = calculate_dataframe(
        frame, GrowthChartsCalculator(), indicator="wfa", measurement="mass", index="age", sex="sex"
    )
    assert list(result.index) == [4, 9]
    assert "zscore" not in frame
    assert result["zscore"].notna().all()
    with pytest.raises(ValueError):
        calculate_dataframe(
            frame,
            GrowthChartsCalculator(),
            indicator="wfa",
            measurement="mass",
            index="age",
            sex="sex",
            output="mass",
        )
    bad = frame.copy()
    bad.loc[4, "mass"] = -1
    coerced = calculate_dataframe(
        bad,
        GrowthChartsCalculator(),
        indicator="wfa",
        measurement="mass",
        index="age",
        sex="sex",
        errors="coerce",
    )
    assert pd.isna(coerced.loc[4, "zscore"])


def test_dataframe_vectorized_matches_scalar(monkeypatch: pytest.MonkeyPatch) -> None:
    pd = pytest.importorskip("pandas")
    from pedgrowth.pandas_integration import calculate_dataframe

    calculator = GrowthChartsCalculator()
    frame = pd.DataFrame(
        {
            "weight": [10.4, 12.0, 11.2, 14.5, 15.0, 8.0],
            "age": [22.45, 30.0, 24.0, 40.0, 42.0, 11.0],
            "sex": ["M", "F", "M", "F", "M", "F"],
        },
        index=[1, 1, 3, 4, 4, 6],
    )
    calls: list[int] = []
    original = calculator.zscores_numpy

    def recording(*args: object, **kwargs: object) -> object:
        calls.append(len(args[1]))  # type: ignore[arg-type]
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(calculator, "zscores_numpy", recording)
    output = calculate_dataframe(
        frame, calculator, indicator="wfa", measurement="weight", index="age", sex="sex"
    )
    assert sorted(calls) == [3, 3]
    expected = [calculator.wfa(float(row.weight), float(row.age), row.sex) for row in frame.itertuples()]
    assert output["zscore"].to_list() == pytest.approx(expected, abs=1e-10)
    assert list(output.index) == list(frame.index)


def test_dataframe_coerce_mixed_invalid() -> None:
    pd = pytest.importorskip("pandas")
    from pedgrowth.pandas_integration import calculate_dataframe

    frame = pd.DataFrame({"mass": [10.0, -1.0, 12.0], "age": [12.0, 24.0, 9999.0], "sex": ["M", "F", "M"]})
    output = calculate_dataframe(
        frame,
        GrowthChartsCalculator(),
        indicator="wfa",
        measurement="mass",
        index="age",
        sex="sex",
        errors="coerce",
    )
    assert pd.notna(output.loc[0, "zscore"])
    assert pd.isna(output.loc[1, "zscore"])
    assert pd.isna(output.loc[2, "zscore"])
