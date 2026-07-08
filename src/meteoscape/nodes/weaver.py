"""`Weaver` - the build-time graph constructor.

From producers' `Capability` + policy config it wires the entire static DAG and allocates every
`Store`, then steps out (absent from the request path). Takes plain config values by injection, never
the `config.py` type. See architecture.md ("Config, Registry, Weaver").
"""

from __future__ import annotations

from collections.abc import Sequence

from ..manifold.core import Manifold
from .providers.base import Provider


class Weaver:
    def weave(self, providers: Sequence[Provider], priority: Sequence[str]) -> Manifold:
        """Wire the static DAG: wrap each Provider in a `Reservoir(store, provider)` (the source role),
        build the top Arbiter, and wrap it in the best-view `Reservoir` - allocating every `Store`."""
        raise NotImplementedError
