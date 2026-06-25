"""The `Normalizer` protocol + shared conversion utilities (utilities land with the first provider).

A Normalizer maps a vendor's shape to canonical *semantics* (parameter identity, units, time
encoding) in native geometry - vendor knowledge, so it lives inside a Provider. Distinct from
homogenization (geometric/temporal sampling), which is the Reservoir's read-back.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ...manifold.core import Coverage, Selection


@runtime_checkable
class Normalizer(Protocol):
    def normalize(self, raw: object, selection: Selection) -> Coverage: ...
