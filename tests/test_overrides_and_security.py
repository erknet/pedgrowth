"""CSV table overrides and source-security invariants."""

from __future__ import annotations

import ast
import csv
import hashlib
import shutil
from pathlib import Path

import pytest
from pedgrowth import GrowthChartsCalculator
from pedgrowth.exceptions import DataError

ROOT = Path(__file__).resolve().parents[1]
BUILTIN_WFA = ROOT / "validation" / "source_data" / "who_weight_for_age_boys.csv"
TABLE_NAME = "who_weight_for_age_boys"


def _modified_reference(tmp_path: Path) -> Path:
    target = tmp_path / "replacement.csv"
    with BUILTIN_WFA.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        row["m"] = str(float(row["m"]) * 1.1)
    with target.open("w", encoding="utf-8", newline="") as result:
        writer = csv.DictWriter(result, fieldnames=["sex", "index", "l", "m", "s", "sigma"])
        writer.writeheader()
        writer.writerows(rows)
    return target


def test_one_table_override_is_local_and_preserves_female(tmp_path):
    replacement = _modified_reference(tmp_path)
    baseline = GrowthChartsCalculator()
    modified = GrowthChartsCalculator(table_overrides={TABLE_NAME: replacement})
    other = GrowthChartsCalculator()

    assert modified.wfa(10.4, 22.45, "M") != pytest.approx(baseline.wfa(10.4, 22.45, "M"))
    assert modified.wfa(10.4, 22.45, "F") == pytest.approx(baseline.wfa(10.4, 22.45, "F"))
    assert other.wfa(10.4, 22.45, "M") == pytest.approx(baseline.wfa(10.4, 22.45, "M"))
    assert modified.lhfa(84.8, 22.45, "M") == pytest.approx(baseline.lhfa(84.8, 22.45, "M"))
    assert modified.table_override_hashes == {
        TABLE_NAME: hashlib.sha256(replacement.read_bytes()).hexdigest()
    }

    # CSV is snapshot-loaded, so subsequent file edits don't silently update the calculator.
    replacement.write_text("bad", encoding="utf-8")
    assert modified.wfa(10.4, 22.45, "M") != pytest.approx(baseline.wfa(10.4, 22.45, "M"))


def test_override_rejects_unknown_table_and_disabled_cdc(tmp_path):
    with pytest.raises(DataError, match="Unknown"):
        GrowthChartsCalculator(table_overrides={"unknown": tmp_path / "x.csv"})
    with pytest.raises(DataError, match="disabled"):
        GrowthChartsCalculator(table_overrides={"cdc_bmi_for_age": tmp_path / "x.csv"})
    with pytest.raises(DataError, match="regular file"):
        GrowthChartsCalculator(table_overrides={TABLE_NAME: tmp_path / "missing.csv"})


@pytest.mark.parametrize(
    "bad_value",
    ['__import__("os").system("echo unsafe")', "nan", "-1", "0", "1e9999"],
)
def test_data_only_invalid_csv_coefficients_rejected(tmp_path, bad_value):
    with BUILTIN_WFA.open(newline="", encoding="utf-8") as source:
        lines = list(csv.reader(source))
    lines[1][3] = bad_value
    replacement = tmp_path / "bad.csv"
    with replacement.open("w", newline="", encoding="utf-8") as output:
        csv.writer(output).writerows(lines)
    with pytest.raises(DataError):
        GrowthChartsCalculator(table_overrides={TABLE_NAME: replacement})


def test_wrong_sex_partition_and_missing_sigma_rejected(tmp_path):
    cdc_name = "cdc_bmi_for_age"
    original = ROOT / "validation" / "source_data" / (cdc_name + ".csv")
    target = tmp_path / "bad-sex.csv"
    with original.open(newline="", encoding="utf-8") as source:
        lines = list(csv.reader(source))
    for line in lines[1:]:
        line[0] = "M"
    with target.open("w", newline="", encoding="utf-8") as output:
        csv.writer(output).writerows(lines)
    with pytest.raises(DataError):
        GrowthChartsCalculator(include_cdc=True, table_overrides={cdc_name: target})

    target = tmp_path / "missing-sigma.csv"
    with original.open(newline="", encoding="utf-8") as source:
        lines = list(csv.reader(source))
    lines[1][5] = ""
    with target.open("w", newline="", encoding="utf-8") as output:
        csv.writer(output).writerows(lines)
    with pytest.raises(DataError, match="sigma"):
        GrowthChartsCalculator(include_cdc=True, table_overrides={cdc_name: target})


def test_oversized_override_rejected(tmp_path):
    oversized = tmp_path / "oversized.csv"
    with oversized.open("wb") as out:
        out.truncate(10_000_001)
    with pytest.raises(DataError, match="exceeds"):
        GrowthChartsCalculator(table_overrides={TABLE_NAME: oversized})


def test_valid_exact_copy_produces_identical_results(tmp_path):
    target = tmp_path / "original.csv"
    shutil.copy2(BUILTIN_WFA, target)
    modified = GrowthChartsCalculator(table_overrides={TABLE_NAME: target})
    assert modified.wfa(10.4, 22.45, "M") == pytest.approx(GrowthChartsCalculator().wfa(10.4, 22.45, "M"))


def test_no_dynamic_execution_primitives_in_runtime_or_refresh_source():
    """Block accidental addition of dynamic execution/deserialization calls."""
    sources = list((ROOT / "packages").glob("*/src/**/*.py"))
    sources.extend((ROOT / "scripts").glob("*.py"))
    prohibited_calls = {"eval", "exec", "compile", "__import__"}
    prohibited_attributes = {
        ("pickle", "load"),
        ("pickle", "loads"),
        ("marshal", "load"),
        ("marshal", "loads"),
        ("dill", "load"),
        ("dill", "loads"),
        ("cloudpickle", "load"),
        ("cloudpickle", "loads"),
        ("os", "system"),
        ("yaml", "load"),
        ("yaml", "unsafe_load"),
        ("subprocess", "run"),
        ("subprocess", "Popen"),
    }
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                assert node.func.id not in prohibited_calls, f"{source}: {node.lineno}"
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                pair = (node.func.value.id, node.func.attr)
                if pair == ("subprocess", "run") and source.name == "build_distributions.py":
                    # Monorepo build orchestration necessarily launches the
                    # trusted Python build command and the local legal-rights
                    # verifier. It must not execute untrusted source text or
                    # use the shell. All runtime/refresh modules remain barred.
                    assert node.args and isinstance(node.args[0], ast.List)
                    command = node.args[0].elts
                    assert command and isinstance(command[0], ast.Attribute)
                    assert isinstance(command[0].value, ast.Name)
                    assert (command[0].value.id, command[0].attr) == ("sys", "executable")
                    assert not any(keyword.arg == "shell" for keyword in node.keywords)
                    assert any(
                        keyword.arg == "check"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                        for keyword in node.keywords
                    )
                    continue
                if pair == ("subprocess", "run") and source.name == "check_namespace_installations.py":
                    # Isolated packaging QA may invoke the known local venv
                    # interpreter only, never an arbitrary external process.
                    assert node.args and isinstance(node.args[0], ast.List)
                    argv = node.args[0].elts
                    assert argv and isinstance(argv[0], ast.Call)
                    assert isinstance(argv[0].func, ast.Name) and argv[0].func.id == "str"
                    assert argv[0].args and isinstance(argv[0].args[0], ast.Name)
                    assert argv[0].args[0].id == "python"
                    assert not any(keyword.arg == "shell" for keyword in node.keywords)
                    assert any(
                        keyword.arg == "check"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                        for keyword in node.keywords
                    )
                    continue
                if pair == ("subprocess", "run") and source.name == "check_public_source.py":
                    # Publication hygiene may inspect only the local Git index,
                    # with a hard-coded read-only argv and without a shell.
                    assert node.args and isinstance(node.args[0], ast.List)
                    command = node.args[0].elts
                    assert [value.value for value in command if isinstance(value, ast.Constant)] == [
                        "git",
                        "ls-files",
                        "--cached",
                        "-z",
                    ]
                    assert len(command) == 4
                    assert not any(keyword.arg == "shell" for keyword in node.keywords)
                    assert any(
                        keyword.arg == "check"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                        for keyword in node.keywords
                    )
                    continue
                assert pair not in prohibited_attributes, f"{source}: {node.lineno}"
