"""Deterministic public API manifest using Python AST; never imports the package."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

ROOT = Path("packages")


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    a = node.args
    positional = a.posonlyargs + a.args
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(a.defaults)) + a.defaults
    params = []
    for index, arg in enumerate(positional):
        default_value = defaults[index]
        params.append(
            {
                "name": arg.arg,
                "kind": "posonly" if index < len(a.posonlyargs) else "poskw",
                "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
                "default": ast.unparse(default_value) if default_value is not None else None,
            }
        )
    if a.vararg:
        params.append(
            {
                "name": a.vararg.arg,
                "kind": "vararg",
                "annotation": ast.unparse(a.vararg.annotation) if a.vararg.annotation else None,
                "default": None,
            }
        )
    for arg, default in zip(a.kwonlyargs, a.kw_defaults, strict=True):
        params.append(
            {
                "name": arg.arg,
                "kind": "kwonly",
                "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
                "default": ast.unparse(default) if default else None,
            }
        )
    if a.kwarg:
        params.append(
            {
                "name": a.kwarg.arg,
                "kind": "varkw",
                "annotation": ast.unparse(a.kwarg.annotation) if a.kwarg.annotation else None,
                "default": None,
            }
        )
    return {
        "parameters": params,
        "returns": ast.unparse(node.returns) if node.returns else None,
        "async": isinstance(node, ast.AsyncFunctionDef),
        "decorators": sorted(
            ast.unparse(d)
            for d in node.decorator_list
            if ast.unparse(d)
            in ("property", "classmethod", "staticmethod", "abc.abstractmethod", "abstractmethod")
        ),
    }


def is_overload(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        ast.unparse(decorator) in {"overload", "typing.overload", "typing_extensions.overload"}
        for decorator in node.decorator_list
    )


def manifest() -> dict[str, Any]:
    modules = {}
    roots = sorted(ROOT.glob("*/src"))
    for path in sorted(file for source_root in roots for file in source_root.rglob("*.py")):
        if any(x in ("testdata", "__pycache__") for x in path.parts):
            continue
        source_root = next(parent for parent in path.parents if parent.name == "src")
        module = ".".join(path.relative_to(source_root).with_suffix("").parts)
        if module.endswith(".__init__"):
            module = module[:-9]
        tree = ast.parse(path.read_text())
        explicit = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
            ):
                try:
                    explicit = set(ast.literal_eval(node.value))
                except (ValueError, TypeError):
                    pass
        items = {}
        module_overloads: dict[str, list[dict[str, Any]]] = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                if explicit is None or node.name in explicit:
                    if is_overload(node):
                        module_overloads.setdefault(node.name, []).append(signature(node))
                    else:
                        items[node.name] = {"kind": "function", **signature(node)}
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                if explicit is not None and node.name not in explicit:
                    continue
                members = {}
                method_overloads: dict[str, list[dict[str, Any]]] = {}
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                        not child.name.startswith("_") or child.name == "__init__"
                    ):
                        if is_overload(child):
                            method_overloads.setdefault(child.name, []).append(signature(child))
                        else:
                            members[child.name] = signature(child)
                    elif isinstance(child, (ast.Assign, ast.AnnAssign)):
                        targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                        for t in targets:
                            if isinstance(t, ast.Name) and not t.id.startswith("_"):
                                value = child.value
                                members[t.id] = {
                                    "kind": "attribute",
                                    "annotation": ast.unparse(child.annotation)
                                    if isinstance(child, ast.AnnAssign) and child.annotation
                                    else None,
                                    # Enum values and public class constants are API contracts.
                                    "value": ast.unparse(value) if value is not None else None,
                                }
                for name, overload_signatures in method_overloads.items():
                    members.setdefault(name, {})["overloads"] = overload_signatures
                items[node.name] = {
                    "kind": "class",
                    "bases": [ast.unparse(b) for b in node.bases],
                    "members": members,
                }
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if not isinstance(target, ast.Name) or target.id.startswith("_"):
                        continue
                    if explicit is not None and target.id not in explicit:
                        continue
                    items[target.id] = {
                        "kind": "constant",
                        "value": ast.unparse(node.value) if node.value is not None else None,
                        "annotation": ast.unparse(node.annotation)
                        if isinstance(node, ast.AnnAssign) and node.annotation
                        else None,
                    }
            elif isinstance(node, (ast.ImportFrom, ast.Import)):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if (explicit is not None and name in explicit) or (
                        explicit is None
                        and not name.startswith("_")
                        and isinstance(node, ast.ImportFrom)
                        and node.level > 0
                    ):
                        items[name] = {"kind": "export", "source": ast.unparse(node)}
        for name, overload_signatures in module_overloads.items():
            items.setdefault(name, {"kind": "function"})["overloads"] = overload_signatures
        if explicit is not None:
            for name in explicit:
                if name not in items and name != "__version__":
                    items[name] = {"kind": "exported_constant"}
        if items:
            modules[module] = items
    return {"schema_version": 1, "modules": modules}


def classify(old: dict[str, Any], new: dict[str, Any]) -> tuple[str, list[str]]:
    changes = []
    additions = []

    def compare(a: Any, b: Any, key: str) -> None:
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(a):
                if k not in b:
                    changes.append(f"removed: {key}.{k}")
                else:
                    compare(a[k], b[k], f"{key}.{k}")
            for k in sorted(b.keys() - a.keys()):
                additions.append(f"added: {key}.{k}")
        elif a != b:
            changes.append(f"changed: {key}")

    if old.get("schema_version") != new.get("schema_version"):
        return "major", ["schema format changed"]
    compare(old["modules"], new["modules"], "modules")
    return ("major" if changes else "minor" if additions else "patch", changes + additions)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="api-schema.json")
    p.add_argument("--compare")
    args = p.parse_args()
    current = manifest()
    Path(args.output).write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    if args.compare:
        change, details = classify(json.loads(Path(args.compare).read_text()), current)
        print(change)
        for detail in details:
            print(detail)
