"""Structural and registration guarantees of the native multi-project monorepo."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import json
import tomllib
from pathlib import Path

import pytest
from pedgrowth import (
    AgeDefinition,
    AgeType,
    AgeUnit,
    GrowthChartsCalculator,
    ReferenceProvider,
    ReferenceRegistry,
    available_plans,
    available_providers,
    create_plan,
)
from pedgrowth.exceptions import DataError
from pedgrowth.registry import ReferenceCandidate
from pedgrowth.tables import TableType

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
CORE = PACKAGES / "pedgrowth" / "src" / "pedgrowth"


def test_core_source_contains_no_provider_code_or_fixtures() -> None:
    assert not (ROOT / "setup.py").exists()
    assert not (ROOT / "MANIFEST.in").exists()
    assert sorted(p.name for p in (CORE / "data").glob("*.py")) == ["__init__.py"]
    assert not (CORE / "testdata").exists()
    assert not (CORE / "tests.py").exists()
    assert not (CORE / "intergrowth.py").exists()
    assert not (CORE / "intergrowth_tables.py").exists()
    assert not (CORE / "tables" / "who").exists()
    assert not (CORE / "tables" / "cdc").exists()
    for filename in CORE.rglob("*.py"):
        tree = ast.parse(filename.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("pedgrowth.data.")
            elif isinstance(node, ast.Import):
                assert not any(alias.name.startswith("pedgrowth.data.") for alias in node.names)


def test_each_distribution_owns_one_source_namespace() -> None:
    expected = {
        "pedgrowth": "pedgrowth",
        "pedgrowth-data-who2006": "pedgrowth.data.who2006",
        "pedgrowth-data-who2007": "pedgrowth.data.who2007",
        "pedgrowth-data-cdc": "pedgrowth.data.cdc",
        "pedgrowth-data-intergrowth": "pedgrowth.data.intergrowth",
    }
    for project, module in expected.items():
        path = PACKAGES / project
        metadata = tomllib.loads((path / "pyproject.toml").read_text())
        assert metadata["project"]["name"] == project
        assert (path / "src" / Path(*module.split(".")) / "__init__.py").is_file()
        assert metadata["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
        assert not (path / "src" / Path(*module.split(".")) / "tests.py").exists()
        assert not (path / "src" / Path(*module.split(".")) / "testdata").exists()
        assert not (path / "src" / Path(*module.split(".")) / "tests").exists()
        if project != "pedgrowth":
            assert not (path / "src" / "pedgrowth" / "__init__.py").exists()
            assert not (path / "src" / "pedgrowth" / "data" / "__init__.py").exists()
            ep = metadata["project"]["entry-points"]["pedgrowth.references"]
            assert set(ep) == {project.removeprefix("pedgrowth-data-")}
            assert ep[project.removeprefix("pedgrowth-data-")] == module + ":register"
            assert (path / "src" / Path(*module.split(".")) / "data" / "SOURCE_LICENSE_MATRIX.json").exists()


def test_shared_namespace_imports_without_legacy_aliases() -> None:
    """The five wheels share pedgrowth.data, but no provider overwrites core."""
    import pedgrowth

    assert pedgrowth.__file__ is not None
    assert importlib.import_module("pedgrowth.data").__path__
    for family in ("cdc", "who2006", "who2007", "intergrowth"):
        module = importlib.import_module("pedgrowth.data." + family)
        assert callable(module.register)
        assert module.__name__ == "pedgrowth.data." + family
        assert importlib.util.find_spec("pedgrowth_data_" + family) is None
    from pedgrowth.data.cdc import CdcClinicalPlan

    assert callable(CdcClinicalPlan)


def test_plugins_register_their_plans_and_tables() -> None:
    assert set(available_providers()) == {"who2006", "who2007", "cdc", "intergrowth"}
    assert {"who", "who2007", "cdc", "cdc_clinical", "intergrowth"} <= set(available_plans())
    who = create_plan("who")
    adolescent = create_plan("who2007")
    assert len(who.tables()) == 24
    assert len(adolescent.tables()) == 6
    age = AgeDefinition(AgeType.CHRONOLOGICAL, AgeUnit.MONTHS)
    result = GrowthChartsCalculator(plan=adolescent).calculate(
        indicator="wfa", measurement=24, sex="M", age=72, age_definition=age
    )
    assert result.reference_id.startswith("who2007_")


def test_registry_rejects_duplicate_extension_names() -> None:
    registry = ReferenceRegistry()
    registration = ReferenceProvider(name="fictional", family="fictional", module="fictional")
    registry.register(registration)
    with pytest.raises(DataError, match="Duplicate reference provider"):
        registry.register(registration)


def test_generic_registry_family_selection_candidate() -> None:
    candidate = ReferenceCandidate(TableType.WeightForAge, coordinate_offset=0.0)
    assert candidate.kind is TableType.WeightForAge
    assert candidate.measurement_offset == 0.0


def test_research_validation_snapshots_never_live_in_core() -> None:
    source = ROOT / "validation" / "source_data"
    assert (source / "SOURCES.json").is_file()
    assert (source / "SOURCE_LICENSES.json").is_file()
    assert (ROOT / "tests" / "fixtures").is_dir()
    assert len(json.loads((source / "SOURCES.json").read_text())["tables"]) == 33
