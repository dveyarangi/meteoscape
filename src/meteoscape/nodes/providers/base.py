"""Provider leaf Manifold: the composable fetch pipeline.

A vendor-specific leaf that contributes native, normalized Coverages: adapter (auth / HTTP /
endpoints) + its Normalizer + capability / cadence / grid declarations. Stateless, no storage, no
children; authors the Coverage's provenance (a single-fetch `Uniform` plane) at fetch. Its
`capability` is a `FootprintCapability` leaf - per-parameter covered footprints (a request-time-dynamic
temporal reach is a declared seam, ADR-0004). See architecture.md ("Provider").
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
