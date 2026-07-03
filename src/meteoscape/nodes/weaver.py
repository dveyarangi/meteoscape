"""`Weaver` - the build-time graph constructor.

From producers' `Capability` + policy config it wires the entire static DAG and allocates every
`Store`, then steps out (absent from the request path). Takes plain config values by injection, never
the `config.py` type. See architecture.md ("Config, Registry, Weaver").
"""

from __future__ import annotations

from collections.abc import Sequence

from ..manifold.core import Manifold
from .source import Source


class Weaver:
    def weave(self, sources: Sequence[Source], priority: Sequence[str]) -> Manifold:
        raise NotImplementedError
