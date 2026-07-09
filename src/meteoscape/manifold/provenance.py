"""Provenance - the Coverage's origin plane, aligned over parameter x geometry-point.

Origin varies over **two** axes - parameter and geometry point - so it is a pluggable `ProvenanceField`
plane (peer of `domain` / `ranges`), not a per-`ParameterData` attribute; that is what lets the Arbiter
assemble one Coverage from many single-origin sources. v1 builds the `Uniform` and `PerParameter` planes
(`PerPoint` is a declared seam) over both `Origin` kinds - atomic and synthetic (the latter a
Calculator's derived-wind lineage).

See ADR-0003.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from ..catalog.vocabulary import ParameterId
from ..identity import SourceKey


class Origin:
    """Root of the origin union (atomic | synthetic) - what a value derives from."""


@dataclass(frozen=True)
class AtomicOrigin(Origin):
    """A single upstream fetch, authored in full at fetch time.

    `source` is the producing `SourceKey`; `issue_time` is the run identity (the forecast issuance the
    values came from), carried here rather than as a Domain axis (ADR-0002).
    """

    source: SourceKey
    issue_time: datetime


class SyntheticOrigin(Origin):
    """Derived from multiple parent provenances (its lineage) - a Calculator's output (v1: the derived
    wind views over their `wind_u` / `wind_v` inputs). Concrete lineage shape lands with behaviour."""


@dataclass(frozen=True)
class Provenance:
    """One origin record - what a (parameter, point) value derives from.

    Freshness reads off `expiration` (the provider's `CadenceDef.expiration`, `A + Δ + L`; ADR-0003):
    fresh while `expiration > now`.
    """

    origin: Origin
    fetched_at: datetime
    expiration: datetime
    # No native-fidelity field: after read-back homogenization the Coverage's Domain is the request
    # lattice; the offering's native resolution is recoverable from `origin`'s SourceKey. Ranking of
    # multi-resolution offerings reads footprint Domain axis steps (concern #20), not a provenance field.


class ProvenanceField(ABC):
    """A Coverage's provenance plane over (parameter, geometry-point).

    `summary(parameter)` is the O(1) parameter-level freshness / origin handle; `at(parameter, i)` is
    the exact per-cell record. Representations differ only in which axes they vary over.
    """

    @abstractmethod
    def summary(self, parameter: ParameterId) -> Provenance:
        """The coarse, point-independent provenance for `parameter` (the freshness handle)."""
        ...

    @abstractmethod
    def at(self, parameter: ParameterId, i: int) -> Provenance:
        """The exact provenance at `parameter`'s i-th geometry point."""
        ...


@dataclass(frozen=True)
class Uniform(ProvenanceField):
    """One origin for the whole Coverage - every parameter, every point (a single-fetch Source)."""

    value: Provenance

    def summary(self, parameter: ParameterId) -> Provenance:
        return self.value

    def at(self, parameter: ParameterId, i: int) -> Provenance:
        return self.value


@dataclass(frozen=True)
class PerParameter(ProvenanceField):
    """One origin per parameter, uniform over geometry - the assembled best view (v1).

    Each parameter's slice is single-origin: the Arbiter never splices origins *within* a parameter
    (cross-origin folding over geometry is the reconciler's `PerPoint` job).
    """

    by_parameter: Mapping[ParameterId, Provenance]

    def summary(self, parameter: ParameterId) -> Provenance:
        return self.by_parameter[parameter]

    def at(self, parameter: ParameterId, i: int) -> Provenance:
        return self.by_parameter[parameter]


class PerPoint(ProvenanceField):
    """Declared seam: origin varies over geometry - consensus / feather / mosaic, the full
    parameter x point corner. Not built in v1."""

    @abstractmethod
    def summary(self, parameter: ParameterId) -> Provenance: ...

    @abstractmethod
    def at(self, parameter: ParameterId, i: int) -> Provenance: ...
