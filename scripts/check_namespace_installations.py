"""Exercise namespace imports from isolated wheel installations.

Only native built wheels are installed. Neither the monorepo checkout nor the
developer's editable environment may satisfy an import by accident.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import tomllib
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = str(tomllib.loads((ROOT / "packages/pedgrowth/pyproject.toml").read_text())["project"]["version"])
CORE = f"pedgrowth-{VERSION}-py3-none-any.whl"
FAMILIES = ("who2006", "who2007", "cdc", "intergrowth")
SCRIPTS = {
    "core": """
from pedgrowth import GrowthChartsCalculator, available_providers
import importlib.util
assert available_providers() == ()
from pedgrowth.data import download_missing_dependencies
assert importlib.util.find_spec("pedgrowth.data") is not None
assert download_missing_dependencies() == {}
assert importlib.util.find_spec("pedgrowth_data_cdc") is None
print("Core-only namespace PASS")
""",
    "cdc": """
from pedgrowth import GrowthChartsCalculator, available_providers
from pedgrowth.data.cdc import CdcPlan, CdcClinicalPlan
import importlib.util
assert available_providers() == ("cdc",)
assert importlib.util.find_spec("pedgrowth_data_cdc") is None
assert callable(CdcClinicalPlan)
from pedgrowth.registry import registry
assert len(registry.tables("cdc")) == 9
assert callable(CdcPlan)
print("CDC-only namespace PASS")
""",
    "who2007": """
from pedgrowth import available_providers
from pedgrowth.data.who2007 import Who2007Plan
from pedgrowth.data import download_missing_dependencies
from pedgrowth.registry import registry
import importlib.util
assert available_providers() == ("who2007",)
assert importlib.util.find_spec("pedgrowth_data_who2007") is None
assert len(registry.tables("who")) == 6
assert callable(Who2007Plan)
assert callable(download_missing_dependencies)
print("WHO2007-only namespace PASS")
""",
    "all": """
import importlib.util
from pedgrowth import GrowthChartsCalculator, available_plans, available_providers, AgeDefinition, AgeUnit, AgeType
from pedgrowth.data.cdc import CdcClinicalPlan, CdcPlan
from pedgrowth.data import download_missing_dependencies
from pedgrowth.data.who2006 import WhoPlan
from pedgrowth.data.who2007 import Who2007Plan
from pedgrowth.data.intergrowth import IntergrowthPlan
from pedgrowth.registry import registry
assert set(available_providers()) == {"who2006", "who2007", "cdc", "intergrowth"}
assert len(registry.tables("who")) == 24
assert len(registry.tables("cdc")) == 9
assert len(registry.tables("intergrowth")) == 7
assert callable(download_missing_dependencies)
assert len(available_plans()) >= 7
assert all(callable(p) for p in (WhoPlan, Who2007Plan, IntergrowthPlan))
for family in ("cdc", "who2006", "who2007", "intergrowth"):
    assert importlib.util.find_spec("pedgrowth_data_" + family) is None
assert GrowthChartsCalculator(plan=CdcPlan()).plan is not None
print("All providers share pedgrowth.data without collision PASS")
""",
}


def check(directory: Path) -> None:
    directory = directory.resolve()
    if not directory.is_dir():
        raise ValueError("Native wheelhouse does not exist")
    wheels = {
        family: directory / ("pedgrowth_data_" + family + f"-{VERSION}-py3-none-any.whl")
        for family in FAMILIES
    }
    core = directory / CORE
    if not core.is_file() or any(not path.is_file() for path in wheels.values()):
        raise ValueError("Expected all five version-locked native wheels")
    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pedgrowth-namespace-", dir=local) as temporary:
        root = Path(temporary)
        variants = {
            "core": (core,),
            "cdc": (core, wheels["cdc"]),
            "who2007": (core, wheels["who2007"]),
            "all": (core, *wheels.values()),
        }
        for name, wheel_files in variants.items():
            venv_path = root / name
            venv.EnvBuilder(with_pip=True).create(venv_path)
            python = venv_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            subprocess.run(  # noqa: S603 - known local interpreter
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-deps",
                    "--disable-pip-version-check",
                    *(str(path) for path in wheel_files),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=90,
            )
            result = subprocess.run(  # noqa: S603 - known local interpreter
                [str(python), "-B", "-c", SCRIPTS[name]],
                cwd=root,
                env={
                    key: value
                    for key, value in os.environ.items()
                    if key not in ("PEDGROWTH_REFERENCE_DIR", "PYTHONPATH")
                },
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            print(result.stdout.strip())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("wheelhouse", type=Path)
    options = parser.parse_args()
    check(options.wheelhouse)
