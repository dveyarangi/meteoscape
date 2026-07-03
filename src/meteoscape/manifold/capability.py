"""`Capability` - what a Manifold can serve, and the Arbiter's admission predicate.

A Manifold facet: per emitted parameter it advertises the `(ParameterDef, Domain)` it offers. There is
no separate clause/extent type because vertical offset and accumulation window are geometry on the
`Domain` (a Z `Cell`, a `valid_time` `Cell`'s `bounds`). A realized `Coverage` exposes it (its params on
its one sampled `Domain`); a `Provider` declares it; composing it up the graph (Arbiter / Reservoir /
Calculator) and a Provider's request-time-dynamic temporal reach are open (concern #16).

`serves` takes the `ParameterDef`, not just the `Domain`, because the resampler is entailed by the
parameter's `(scale, statistic, extent_scaling)`: `Domain.contains` is only the geometric half, and
extent-reachable aggregation (6h from 3h) is not containment. See ADR-0004.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..catalog.vocabulary import ParameterDef, ParameterId
from .domain import Domain


@dataclass(frozen=True)
class Capability:
    """Per-parameter `(ParameterDef, Domain)` offer plus the `serves` admission predicate."""

    served: Mapping[ParameterId, tuple[ParameterDef, Domain]]

    def serves(self, parameter: ParameterId, requested: Domain) -> bool:
        raise NotImplementedError
