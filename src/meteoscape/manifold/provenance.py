"""Provenance - the Coverage's origin plane, aligned over parameter x geometry-point.

Origin varies over **two** axes - parameter and geometry point - so it is a pluggable `ProvenanceField`
plane (peer of `domain` / `ranges`), not a per-`ParameterData` attribute; that is what lets the Arbiter
assemble one Coverage from many single-origin sources. v1 builds the `Uniform` and `PerParameter` planes
(`PerPoint` is a declared seam). A lossless, invertible Calculator (v1's derived wind) **propagates** its
input's atomic origin verbatim, so v1 exercises only the **atomic** `Origin`. `SyntheticOrigin` — minted by
a method-bearing or multi-origin derivation — stays a declared seam, unexercised in v1.

See ADR-0003.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from ..identity import SourceKey
from ..parameters import ParameterId


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
    """A composite's record of a derivation - its `lineage` of contributing parents plus a
    calculation-method tag. Minted by a **method-bearing** computation (even over a single shared-origin
    input - the method is what it records) or a **multi-origin** blend (`expiration = min` over parents).
    A lossless, invertible transform is *not* synthetic: it propagates its input's `AtomicOrigin` instead.
    Declared seam - concrete lineage / method shape lands with the first synthetic Calculator (post-v1)."""


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
