"""The `Normalizer` protocol + shared native→canonical conversion utilities.

A Normalizer maps a vendor's shape to canonical *semantics* (parameter identity, units, time
encoding) in native geometry - vendor knowledge, so it lives inside a Provider. The Provider authors
`Provenance` and passes it in; the Normalizer does not take the request Selection (homogenization is
the Reservoir's read-back). Returns one or more native `Coverage` records grouped by shared native
Domain ([ADR-0006](../../../docs/adr/0006-materialization-granularity-and-store-shape.md)).

Conversion factors here are shared by provider normalizers and seed the planned unit catalogue.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ...manifold.core import Coverage
from ...manifold.provenance import Provenance

KMH_TO_MS = 1.0 / 3.6


def kmh_to_ms(value: float) -> float:
    """Convert wind speed from km/h to canonical m/s."""
    return value * KMH_TO_MS


@runtime_checkable
class Normalizer(Protocol):
    def normalize(self, raw: object, provenance: Provenance) -> Sequence[Coverage]: ...
