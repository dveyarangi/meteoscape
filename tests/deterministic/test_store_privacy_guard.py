"""Guard: private store unit types stay inside `nodes/store.py`.

ADR-0006 makes the unit table and its lattices store-private — consumed by `quantize`, the
holdings query, and read-back; never a public node face. The guard is static (same posture as
`test_probe_seam_guard`): an import of `MemoryStore` is fine; naming `_Unit` / `_UnitKey` outside
the module is the leak.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src" / "meteoscape"
_STORE = _SRC / "nodes" / "store.py"
_PRIVATE = frozenset({"_Unit", "_UnitKey"})


def _python_modules() -> list[Path]:
    return sorted(p for p in _SRC.rglob("*.py") if p != _STORE)


def test_store_module_defines_the_private_types() -> None:
    """A guard that guards nothing passes silently — so pin that the privates exist to protect."""
    tree = ast.parse(_STORE.read_text(encoding="utf-8"))
    defined: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            defined.add(node.name)
        elif isinstance(node, ast.TypeAlias):
            defined.add(node.name.id)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined.add(node.target.id)
    assert defined >= _PRIVATE, f"store.py missing private types: {sorted(_PRIVATE - defined)}"


def test_no_module_outside_store_references_private_unit_types() -> None:
    for path in _python_modules():
        used: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                # `store._Unit` reaches the private through the module object — same leak.
                used.add(node.attr)
        leaked = sorted(used & _PRIVATE)
        assert not leaked, f"{path.relative_to(_SRC)} references store privates: {leaked}"
