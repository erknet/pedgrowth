"""Keep public documentation examples synchronized with the installed API.

The examples executed here are trusted, repository-owned snippets. Synthetic
third-party plugin and user-supplied CSV templates are syntax-checked only.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_DOCS = (
    "README.md",
    "packages/pedgrowth/README.md",
    "docs/INTERGROWTH.md",
    "docs/PANDAS.md",
    "docs/EXTENDING_REFERENCES.md",
)


def _python_snippets(document: str) -> list[str]:
    source = (ROOT / document).read_text(encoding="utf-8")
    return re.findall(r"(?:```|~~~)python\n(.*?)(?:```|~~~)", source, flags=re.S)


@pytest.mark.parametrize("path", PUBLIC_DOCS)
def test_all_documented_python_blocks_are_valid_syntax(path: str) -> None:
    blocks = _python_snippets(path)
    assert blocks, path
    for index, example in enumerate(blocks, 1):
        compile(example, f"{path} example {index}", "exec")


@pytest.mark.parametrize(
    "path",
    ("README.md", "packages/pedgrowth/README.md", "docs/INTERGROWTH.md", "docs/PANDAS.md"),
)
def test_current_usage_examples_execute(path: str) -> None:
    snippets = _python_snippets(path)
    if path.endswith("README.md"):
        # The final block shows registration for a fictional third-party package.
        snippets = snippets[:-1]
    scope: dict[str, object] = {"__name__": "__main__"}
    for snippet in snippets:
        exec(compile(snippet, path, "exec"), scope)  # noqa: S102 - trusted checked-in docs


def test_custom_reference_and_study_plan_examples_execute() -> None:
    snippets = _python_snippets("docs/EXTENDING_REFERENCES.md")
    scope: dict[str, object] = {"__name__": "__main__"}
    # The first snippet deliberately requires a user-owned CSV; the later
    # synthetic demonstration table can be constructed without external data.
    for snippet in snippets[1:3]:
        exec(compile(snippet, "docs/EXTENDING_REFERENCES.md", "exec"), scope)  # noqa: S102
    assert isinstance(scope["score"], float)


def test_typed_architecture_example_executes() -> None:
    source = (ROOT / "docs/TYPED_ARCHITECTURE.md").read_text(encoding="utf-8")
    example = source.split("## Example\n", 1)[1].split("\nThe typed NumPy API", 1)[0]
    scope: dict[str, object] = {"__name__": "__main__"}
    exec(compile(textwrap.dedent(example), "docs/TYPED_ARCHITECTURE.md", "exec"), scope)  # noqa: S102
    assert scope["result"].reference_id.startswith("cdc_")


def test_provider_specific_plan_imports_not_documented_from_core() -> None:
    current = (
        ROOT / "README.md",
        ROOT / "packages/pedgrowth/README.md",
        ROOT / "docs/INTERGROWTH.md",
        ROOT / "docs/PANDAS.md",
        ROOT / "docs/TYPED_ARCHITECTURE.md",
        ROOT / "docs/EXTENDING_REFERENCES.md",
    )
    obsolete = re.compile(
        r"from\s+pedgrowth\s+import\s+(?:\([^)]*?\b(?:WhoPlan|CdcPlan|CdcClinicalPlan|IntergrowthPlan|IntergrowthCalculator)\b"
        r"|(?:[^\n]*,\s*)?(?:WhoPlan|CdcPlan|CdcClinicalPlan|IntergrowthPlan|IntergrowthCalculator)\b)",
        re.S,
    )
    for path in current:
        assert not obsolete.search(path.read_text()), str(path)
