"""Provider leaf Manifold: the composable fetch pipeline.

A vendor-specific leaf that contributes native, normalized Coverages: adapter (auth / HTTP /
endpoints) + its Normalizer + capability / cadence / grid declarations. Stateless, no storage, no
children; authors the Coverage's provenance (a single-fetch `Uniform` plane) at fetch. See
architecture.md ("Provider").
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...manifold.capability import Capability
from ...manifold.core import Manifold, Selection


class Provider(ABC):
    @abstractmethod
    def project(self, selection: Selection) -> Manifold: ...

    @property
    @abstractmethod
    def capability(self) -> Capability: ...
