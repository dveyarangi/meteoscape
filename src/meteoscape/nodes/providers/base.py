"""Provider leaf Manifold: the composable fetch pipeline.

A vendor-specific leaf that contributes native, normalized Coverages: adapter (auth / HTTP /
endpoints) + its Normalizer + `CadenceDef` / grid declarations, with a `Clock` injected at build.
Stateless, no storage, no children; authors the Coverage's provenance (a single-fetch `Uniform` plane)
at fetch. Its `capability` is a stable `FootprintCapability` leaf built once from the cadence + clock:
per-parameter footprints with static spatial / Z bounds and a clock-anchored `RollingAxis` on
`valid_time` that rolls with the run anchor (ADR-0003 / ADR-0004). See architecture.md ("Provider").
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...manifold.capability import Capability
from ...manifold.core import Manifold, Selection


class Provider(ABC):
    @abstractmethod
    async def project(self, selection: Selection) -> Manifold: ...

    @property
    @abstractmethod
    def capability(self) -> Capability: ...
