"""Guard: a vendor `Probe` speaks value types only, never the manifold's.

The seam is typed by value on purpose (edge/provider.md): a Probe that never holds a `Clock` cannot
mis-stamp provenance, and one that never narrows a `Domain` cannot mistake an unservable request for a
vendor fault. That buys the rule structurally instead of by review — but only if something checks it,
which is what this is. It guards the *next* Probe more than the shipped one.

Static, not import-based like `test_parity_reader_guard`: a vendor module legitimately imports the
shape wrapper, which legitimately imports the whole manifold, so what is loaded proves nothing. What
matters is the names a vendor module *binds and uses*.
"""

from __future__ import annotations

import ast
from pathlib import Path

_PROVIDERS = Path(__file__).resolve().parents[2] / "src" / "meteoscape" / "nodes" / "providers"

_SHARED = {"__init__.py", "base.py", "timeline.py", "normalization.py"}
"""Not vendor modules: the `Provider` face, the shape wrappers, and the conversion edges."""

_FORBIDDEN = {"Domain", "Selection", "Coverage", "Capability", "Provenance", "Clock"}

_BUILD_FACE_ONLY = {"Clock"}
"""`build(spec, settings, secret, clock, parameters)` is the catalogue's composition face, not the
Probe's — it receives a `Clock` and hands it to the wrapper. Every other manifold type has no
legitimate use anywhere in a vendor module."""


def _vendor_modules() -> list[Path]:
    return sorted(p for p in _PROVIDERS.glob("*.py") if p.name not in _SHARED)


def _imported_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name.rsplit(".", 1)[-1] for alias in node.names)
    return names


def test_vendor_modules_are_discovered() -> None:
    """A guard that guards nothing passes silently — so pin that it found something to check."""
    modules = _vendor_modules()
    assert modules, f"no vendor modules found under {_PROVIDERS}"
    assert any(
        isinstance(node, ast.ClassDef) and node.name.endswith("Probe")
        for path in modules
        for node in ast.parse(path.read_text(encoding="utf-8")).body
    ), "no Probe class found in any vendor module"


def test_vendor_modules_import_no_manifold_types() -> None:
    for path in _vendor_modules():
        imported = _imported_names(ast.parse(path.read_text(encoding="utf-8")))
        leaked = sorted((imported & _FORBIDDEN) - _BUILD_FACE_ONLY)
        assert not leaked, f"{path.name} imports manifold types: {leaked}"


def test_probe_bodies_reference_no_manifold_types() -> None:
    """Including `Clock`: the composition face may hold one, the Probe may not even see it."""
    for path in _vendor_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not (isinstance(node, ast.ClassDef) and node.name.endswith("Probe")):
                continue
            used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            used |= {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
            leaked = sorted(used & _FORBIDDEN)
            assert not leaked, f"{path.name}:{node.name} references manifold types: {leaked}"
