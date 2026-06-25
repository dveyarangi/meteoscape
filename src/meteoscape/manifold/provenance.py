"""Provenance - the per-parameter origin metadata a `ParameterData` carries.

One provenance per `ParameterData`, realized as a `ProvenanceField` (geometry-aligned, so per-point
is additive). An origin is atomic (a single fetch, carrying the run identity `issue_time`) or
synthetic (derived from parent provenances). Freshness reads off `expiration`. v1 builds only the
`Uniform` field and the atomic origin; `PerPoint` and `SyntheticOrigin` are declared seams.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class Origin:
    """Root of the origin union (atomic | synthetic) - what a `ParameterData`'s values derive from."""


@dataclass(frozen=True)
class AtomicOrigin(Origin):
    """A single upstream fetch, authored in full at fetch time.

    Carries the run identity `issue_time` (the forecast issuance the values came from) and the
    producing source - so a reader knows which provider/run produced each value.
    """

    source: str
    issue_time: datetime


class SyntheticOrigin(Origin):
    """Declared seam: derived from multiple parent provenances (its lineage). Not built in v1."""


@dataclass(frozen=True)
class Provenance:
    """Per-parameter origin metadata carried on a `ParameterData`.

    Freshness reads off `expiration` (`fetched_at + cadence`): fresh while `expiration > now`.
    """

    origin: Origin
    fetched_at: datetime
    expiration: datetime
    native_resolution: str | None = None


class ProvenanceField(ABC):
    """Geometry-aligned provenance attribute, with representations differing only in cardinality.

    The O(1) `summary` is the parameter-level handle (built by the producer, never scanned at read).
    `at(i)` is exact per-cell, opt-in.
    """

    @property
    @abstractmethod
    def summary(self) -> Provenance: ...

    @property
    @abstractmethod
    def uniform(self) -> bool: ...

    @abstractmethod
    def at(self, i: int) -> Provenance: ...


@dataclass(frozen=True)
class Uniform(ProvenanceField):
    """Cardinality-1 provenance: one `Provenance` holds for every cell (v1, `priority`)."""

    value: Provenance

    @property
    def summary(self) -> Provenance:
        return self.value

    @property
    def uniform(self) -> bool:
        return True

    def at(self, i: int) -> Provenance:
        return self.value


class PerPoint(ProvenanceField):
    """Declared seam: cardinality-N provenance (consensus / feather). Not built in v1."""

    @property
    @abstractmethod
    def summary(self) -> Provenance: ...

    @property
    @abstractmethod
    def uniform(self) -> bool: ...

    @abstractmethod
    def at(self, i: int) -> Provenance: ...
