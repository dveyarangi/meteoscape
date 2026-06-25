"""Provider leaf Manifold: the composable fetch pipeline.

A vendor-specific leaf that contributes native, normalized Coverages: adapter (auth / HTTP /
endpoints) + its Normalizer + capability / cadence / grid declarations. Stateless, no storage, no
children; authors each `ParameterData`'s full provenance at fetch. The concrete fetch pipeline is
built per-vendor from 001 onward.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...manifold.core import Manifold, Selection
from ..capability import Capability


class Provider(ABC):
    @abstractmethod
    def project(self, selection: Selection) -> Manifold: ...

    @property
    @abstractmethod
    def capability(self) -> Capability: ...
