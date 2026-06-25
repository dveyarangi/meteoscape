"""`Domain` - the coordinate set over the 4 axes, and its v1 regular representation.

A `Domain` is an abstract coordinate set; representations vary behind one interface. Separability is a
*facet* (an optional protocol a representation exposes), not the base type, so a curvilinear geometry
can satisfy the base interface without it. Regularity is **not** a domain capability but a per-axis
*representation*: an `Axis` is a lazy `Sequence[Cell]`, and a `RegularAxis` simply computes its cells
from `(anchor, step, count)` instead of storing them. `issue_time` is **not** an axis - it is a
provenance stamp (ADR-0002/0003).

v1 ships `RegularDomain`; `RectilinearDomain` / `CurvilinearDomain` and `Domain.intersect` are
declared seams (behaviour deferred). The iteration surface here (`enumerate`, `Separable.axis` -> the
`Cell` sequence, `EnumerableDomain` indexing) is the representation-free path serialization and
homogenization bind to (ADR-0002).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol, runtime_checkable

type Coordinate = float | datetime
"""A scalar coordinate on one axis - spatial coordinates are floats, the time axis `T` is a datetime."""

type Step = float | timedelta
"""A spacing between coordinates - a float (spatial) or a `timedelta` (the time axis `T`); a delta, not
a `Coordinate`."""


class AxisName(Enum):
    """The 4 interpolable axes: 3 spatial (representation-agnostic) + time (`T`).

    `T` is the **valid-time** axis - the time a value is valid for (`issue_time` is provenance, not an
    axis). v1's lat/lon point maps onto the spatial axes at the edge; the concrete spatial-ref encoding
    is a deferred parameter convention.
    """

    X = "x"
    Y = "y"
    Z = "z"
    T = "t"


@dataclass(frozen=True)
class Interval:
    """A cell's bounds on one axis - the span a coordinate covers (`lower`..`upper`)."""

    lower: Coordinate
    upper: Coordinate


@dataclass(frozen=True)
class Cell:
    """One position on an axis: its representative `coordinate` and (optional) `bounds`.

    `bounds is None` => an instant / point (zero-width); present => the cell's interval (the
    aggregation / integration window an extensive or windowed parameter reads as its *extent*). The
    `coordinate` lies within the `bounds` by convention (centre, or an edge for period-ending
    accumulations), never by definition - the two are independent, so neither derives from the other.
    """

    coordinate: Coordinate
    bounds: Interval | None


@dataclass(frozen=True)
class Point:
    """A single position over the axes (the element `enumerate()` / `[]` yields): one `Cell` per axis,
    so a position carries its full per-axis geometry - coordinate *and* optional bounds.
    """

    cells: Mapping[AxisName, Cell]


class Axis(ABC):
    """One axis of a `Separable` Domain: a lazy, indexable sequence of `Cell`s.

    The whole contract is `axis[i] -> Cell` + `len(axis)` (iteration provided by the base over those);
    positional, so it aligns with `ParameterData.values[i]`. Columnar coordinate/bounds arrays are a
    derived edge concern (serialization / a future numpy backend), not part of this surface.
    Concretions choose storage: `RegularAxis` computes its cells, an explicit (rectilinear) axis stores
    them.
    """

    name: AxisName
    interpolable: bool

    @abstractmethod
    def __getitem__(self, index: int) -> Cell: ...

    @abstractmethod
    def __len__(self) -> int: ...

    def __iter__(self) -> Iterator[Cell]:
        return (self[i] for i in range(len(self)))


@dataclass(frozen=True)
class RegularAxis(Axis):
    """The uniform axis: cells generated from `anchor` (origin) + `step` (spacing) + `count` (length).

    `self[i].coordinate = anchor + i*step`, generated lazily (stores nothing). `cellular` picks the
    geometry: `True` => each `Cell` spans one step (`bounds = [coord, coord+step]`), `False` => an
    instant (`bounds = None`). Where the coordinate sits within its cell (leading / trailing / centred)
    is the normalizer's convention, encoded in `anchor`. The v1 representation's axis; generation
    behaviour is deferred to the slice that samples (001).
    """

    name: AxisName
    interpolable: bool
    anchor: Coordinate
    step: Step
    count: int
    cellular: bool

    def __getitem__(self, index: int) -> Cell:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError


@runtime_checkable
class Separable(Protocol):
    """Facet: per-axis decomposition. A separable representation exposes its axes."""

    def axis(self, name: AxisName) -> Axis: ...


class Domain(ABC):
    """An abstract coordinate set over the 4 axes - continuous or enumerable. Representations vary
    behind this interface; only the set-algebra (`contains` / `intersect`) is universal. Enumeration is
    the `EnumerableDomain` refinement, so *being* one is the enumerability discriminator - the base
    makes no such claim.
    """

    @abstractmethod
    def contains(self, other: Domain) -> bool:
        """Domain-containment - the Capability filter (this set encloses `other`)."""
        ...

    @abstractmethod
    def intersect(self, other: Domain) -> Domain:
        """Declared seam: geometric intersection. Not implemented in v1."""
        ...


class EnumerableDomain(Domain):
    """The enumerable case of a Domain - a finite, indexable set of coordinate positions.

    A Coverage carries one of these; `ParameterData.values[i]` is positional to `__getitem__(i)` /
    `enumerate()`. The whole enumeration surface lives here, never on the base `Domain`.
    """

    @abstractmethod
    def __getitem__(self, index: int) -> Point: ...

    @abstractmethod
    def __len__(self) -> int: ...

    @abstractmethod
    def enumerate(self) -> Iterator[Point]:
        """Iterate coordinate positions (positional to a Coverage's `ParameterData.values`)."""
        ...


@dataclass(frozen=True)
class RegularDomain(EnumerableDomain):
    """The uniform-grid representation: a `RegularAxis` per axis. The v1 representation.

    Separable (exposes its axes); regularity rides on the axes, not on the domain. Behaviour
    (containment, enumeration, indexing) is deferred to the slices that need it; v1's point/hourly case
    is built in 001.
    """

    axes: Mapping[AxisName, RegularAxis]

    def contains(self, other: Domain) -> bool:
        raise NotImplementedError

    def intersect(self, other: Domain) -> Domain:
        raise NotImplementedError

    def enumerate(self) -> Iterator[Point]:
        raise NotImplementedError

    def __getitem__(self, index: int) -> Point:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError

    def axis(self, name: AxisName) -> Axis:
        return self.axes[name]


class RectilinearDomain(Domain):
    """Declared seam: separable but irregular - holds explicit `Axis`es of stored `Cell`s. Not built
    in v1."""


class CurvilinearDomain(Domain):
    """Declared seam: non-separable geometry (radar slice, satellite swath). Not built in v1."""
