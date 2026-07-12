"""The `Normalizer` protocol + shared conversion utilities (utilities land with the first provider).

A Normalizer maps a vendor's shape to canonical *semantics* (parameter identity, units, time
encoding) in native geometry - vendor knowledge, so it lives inside a Provider. The Provider authors
`Provenance` and passes it in; the Normalizer does not take the request Selection (homogenization is
the Reservoir's read-back).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ...manifold.core import Coverage
from ...manifold.provenance import Provenance


@runtime_checkable
class Normalizer(Protocol):
    def normalize(self, raw: object, provenance: Provenance) -> Coverage: ...
