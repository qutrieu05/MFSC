"""Enforce the layer dependency rules from ARCHITECTURE.md section 7.2 (NFR-MNT-01).

This test is the executable version of the architecture: if a new package appears in
``edge/src/msfc`` it must be declared here, and a package may only import the packages
its layer is allowed to depend on.
"""

from __future__ import annotations

import ast
from pathlib import Path

ALLOWED: dict[str, set[str]] = {
    "core": set(),
    "domain": {"core"},
    "contracts": {"core"},
    "comm": {"core", "contracts"},
    "vision": {"core", "domain"},
    "safety_vision": {"core", "domain"},
    "ocr": {"core", "domain"},
    "decision": {"core", "domain"},
    "storage": {"core", "domain"},
    "analytics": {"core", "domain"},
    "services": {
        "core", "domain", "contracts", "comm", "vision",
        "safety_vision", "ocr", "decision", "storage", "analytics",
    },
    "dashboard": {
        "core", "domain", "contracts", "comm", "storage", "services", "analytics", "sim",
        "vision", "ocr", "decision",
    },
    "sim": {"core", "domain", "contracts", "comm"},
    "cli": {
        "core", "domain", "contracts", "comm", "vision", "safety_vision",
        "ocr", "decision", "storage", "analytics", "services", "dashboard", "sim",
    },
}

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "msfc"


def _imported_packages(path: Path) -> set[str]:
    """Return the ``msfc.<package>`` names imported by one module."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "msfc" and len(parts) > 1:
                    found.add(parts[1])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            parts = node.module.split(".")
            if parts[0] == "msfc" and len(parts) > 1:
                found.add(parts[1])
    return found


def test_every_package_is_declared_in_the_rules() -> None:
    packages = {
        item.name
        for item in PACKAGE_ROOT.iterdir()
        if item.is_dir() and (item / "__init__.py").exists()
    }
    undeclared = sorted(packages - set(ALLOWED))
    assert not undeclared, (
        f"packages {undeclared} are not declared in ALLOWED; "
        "update ARCHITECTURE.md section 7.2 and this test together"
    )


def test_imports_respect_layer_rules() -> None:
    violations: list[str] = []
    for module_path in PACKAGE_ROOT.rglob("*.py"):
        relative = module_path.relative_to(PACKAGE_ROOT)
        if len(relative.parts) == 1:  # msfc/__init__.py and friends
            continue
        package = relative.parts[0]
        allowed = ALLOWED.get(package)
        if allowed is None:
            continue  # reported by test_every_package_is_declared_in_the_rules
        for imported in _imported_packages(module_path):
            if imported != package and imported not in allowed:
                violations.append(f"{relative.as_posix()}: msfc.{package} must not import msfc.{imported}")
    assert not violations, "layer dependency violations:\n" + "\n".join(sorted(violations))
