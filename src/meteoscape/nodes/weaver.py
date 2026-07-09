"""`Weaver` - the build-time graph constructor.

From the read-only `SourceRegistry` (producers keyed by `SourceKey`, each carrying `priority`) + the
derivation registry + store/grid config it wires the entire static DAG and allocates every `Store`,
then steps out (absent from the request path). Ordering rides inside `sources` — never a detached
provider-id list. Takes plain values by injection, never the `config.py` type. See architecture.md
("Config, Registry, Weaver").
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from ..catalog.vocabulary import ParameterId
from ..manifold.core import Manifold
from .calculator import Calculator
from .registry import SourceRegistry


class DerivationRegistry(Protocol):
    """Declared seam: Calculator recipes the Weaver wires into the DAG (v1: derived wind views)."""

    @property
    def calculators(self) -> Mapping[ParameterId, Calculator]: ...


@dataclass(frozen=True)
class StoreConfig:
    """Declared seam: store/grid knobs the Weaver uses when allocating every `Store`."""

    spatial_step: float
    retention_interval: timedelta


class Weaver:
    def weave(
        self,
        sources: SourceRegistry,
        derivations: DerivationRegistry,
        store: StoreConfig,
    ) -> Manifold:
        """Wire the static DAG: wrap each producer in a `Reservoir(store, provider)` (the source role),
        build the top Arbiter (+ Calculators), and wrap it in the best-view `Reservoir` — allocating
        every `Store`."""
        raise NotImplementedError
