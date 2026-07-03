"""`Domain` - the coordinate set over the 4 axes (3 spatial + `valid_time`), and its v1 regular
representation.

Representations vary behind one interface: separability is a *facet* (not the base type) and
regularity is a per-axis choice (`RegularAxis` computes cells from `(anchor, step, count)`), so a
curvilinear geometry can satisfy the base without either. `issue_time` is a provenance stamp, **not**
an axis. v1 ships `RegularDomain`; the other representations and `intersect` are declared seams.

See ADR-0002.
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
    """The 4 field axes: 3 spatial + time (`T` = `valid_time`). Categorical keys (`issue_time`,
    ensembles) are **not** axes (ADR-0002).
    """

    X = "x"
    Y = "y"
    Z = "z"
    T = "t" # valid_time


@dataclass(frozen=True)
class Interval:
    """A cell's bounds on one axis - the span a coordinate covers (`lower`..`upper`)."""

    lower: Coordinate
    upper: Coordinate


@dataclass(frozen=True)
class Cell:
    """One position on an axis: its representative `coordinate` and (optional) `bounds`.

    `bounds is None` => an instant / point; present => the cell's interval (a parameter's extent).
    Invariant: `coordinate` and `bounds` are independent - the coordinate lies within the bounds by
    convention (centre, or an edge for period-ending accumulations), never by definition (ADR-0002).
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

    The whole contract is `axis[i] -> Cell` + `len(axis)`; positional, so it aligns with
    `ParameterData.values[i]`. An axis is pure geometry - it carries no interpolability flag, since
    whether a value may be resampled along it is the parameter's resampler fact, not the axis's
    (ADR-0002).
    """

    name: AxisName

    @abstractmethod
    def __getitem__(self, index: int) -> Cell: ...

    @abstractmethod
    def __len__(self) -> int: ...

    def __iter__(self) -> Iterator[Cell]:
        return (self[i] for i in range(len(self)))


@dataclass(frozen=True)
class RegularAxis(Axis):
    """The uniform axis: cells generated lazily from `anchor` + `step` + `count`.

    `self[i].coordinate = anchor + i*step`. `cellular` picks the geometry: `True` => each `Cell` spans
    one step (`bounds = [coord, coord+step]`), `False` => an instant (`bounds = None`). Where the
    coordinate sits within its cell (leading / trailing / centred) is the normalizer's convention,
    encoded in `anchor`.
    """

    name: AxisName
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
    """An abstract coordinate set over the 4 axes - continuous or enumerable.

    Only the set-algebra (`contains` / `intersect`) is universal; enumeration is the `EnumerableDomain`
    refinement, so *being* one is the enumerability discriminator (ADR-0002).
    """

    @abstractmethod
    def contains(self, other: Domain) -> bool:
        """Domain-containment (this set encloses `other`)."""
        ...

    @abstractmethod
    def intersect(self, other: Domain) -> Domain:
        """Declared seam: geometric intersection. Not implemented in v1."""
        ...


class EnumerableDomain(Domain):
    """The enumerable case of a Domain - a finite, indexable set of coordinate positions.

    Invariant: a Coverage's `ParameterData.values[i]` is positional to `__getitem__(i)` / `enumerate()`.
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
    """The v1 uniform-grid representation: a `RegularAxis` per axis.

    Separable (exposes its axes); regularity rides on the axes, not on the domain.
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
