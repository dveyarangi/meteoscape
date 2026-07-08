"""`Domain` - the coordinate set over the 4 axes (3 spatial + `valid_time`), and its v1 regular
representation.

Representations vary behind one interface: separability is a *facet* (not the base type) and
regularity is a per-axis choice (`RegularAxis` computes cells from `(anchor, step, count)`), so a
curvilinear geometry can satisfy the base without either. `issue_time` is a provenance stamp, **not**
an axis. v1 ships `RegularDomain` (the enumerable grid) and `FootprintDomain` (a continuous provider
reach); the other representations and `intersect` are declared seams.

See ADR-0002.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Mapping
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
    """A span on one axis (`lower`..`upper`) - a `Cell`'s bounds, and an `Axis`'s `extent`."""

    lower: Coordinate
    upper: Coordinate

    def contains(self, other: Interval) -> bool:
        return self.lower <= other.lower and other.upper <= self.upper


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
    """One axis of a `Separable` Domain: the geometry along one named dimension.

    Its universal surface is just its span - `extent` - mirroring `Domain` (set-algebra, not
    enumeration); enumeration is the `EnumerableAxis` refinement. An axis is **pure geometry** - it
    carries no interpolability flag, since whether a value may be resampled along it is the parameter's
    resampler fact, not the axis's (ADR-0002).
    """

    name: AxisName

    @property
    @abstractmethod
    def extent(self) -> Interval:
        """The axis's span (for a `RollingAxis`, resolved against its clock at read)."""
        ...


class EnumerableAxis(Axis):
    """The enumerable refinement of an `Axis`: a lazy, indexable sequence of `Cell`s.

    `axis[i] -> Cell` + `len(axis)`; positional, so it aligns with `ParameterData.values[i]`.
    """

    @abstractmethod
    def __getitem__(self, index: int) -> Cell: ...

    @abstractmethod
    def __len__(self) -> int: ...

    def __iter__(self) -> Iterator[Cell]:
        return (self[i] for i in range(len(self)))


@dataclass(frozen=True)
class RegularAxis(EnumerableAxis):
    """The uniform enumerable axis: cells generated lazily from `anchor` + `step` + `count`.

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

    @property
    def extent(self) -> Interval:
        raise NotImplementedError

    def __getitem__(self, index: int) -> Cell:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError


@dataclass(frozen=True)
class ContinuousAxis(Axis):
    """The plain continuous axis: an explicit span, no cells - a `FootprintDomain`'s spatial / Z axis.

    The unmarked continuous case; `RollingAxis` is the clock-anchored specialization.
    """

    name: AxisName
    interval: Interval

    @property
    def extent(self) -> Interval:
        return self.interval


@dataclass(frozen=True)
class RollingAxis(Axis):
    """The clock-anchored continuous axis: a `FootprintDomain`'s `valid_time` axis.

    `extent` resolves to `[now() - retention, now() + lead]` against the injected clock at read, so this
    axis is deliberately **clock-relative** (the one intentional exception to axis-as-pure-geometry,
    isolated here). Anchor is wall-clock `now()`; reconciling it with the provider's run-phased,
    latency-delayed availability is the anchor-fidelity concern (concern #18, ADR-0004).
    """

    name: AxisName
    lead: timedelta
    retention: timedelta
    now: Callable[[], datetime]

    @property
    def extent(self) -> Interval:
        instant = self.now()
        return Interval(lower=instant - self.retention, upper=instant + self.lead)


@runtime_checkable
class Separable(Protocol):
    """Facet: per-axis decomposition. A separable representation exposes its axes (enumerable or
    continuous)."""

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


@dataclass(frozen=True)
class FootprintDomain(Domain):
    """A producer's declared reach - a **continuous**, `Separable` region (never enumerable), the
    footprint the Capability filter tests against.

    Per-axis bounds: a `ContinuousAxis` on each spatial / Z axis, a clock-anchored `RollingAxis` on
    `valid_time`. `contains` composes **per-axis extent-containment**; its `RollingAxis` makes it
    clock-relative, so admission tracks the provider's rolling horizon while `serves` stays a plain
    `contains`.
    """

    axes: Mapping[AxisName, Axis]

    def contains(self, other: Domain) -> bool:
        raise NotImplementedError

    def intersect(self, other: Domain) -> Domain:
        raise NotImplementedError

    def axis(self, name: AxisName) -> Axis:
        return self.axes[name]


class RectilinearDomain(Domain):
    """Declared seam: separable but irregular - holds explicit `EnumerableAxis`es of stored `Cell`s. Not
    built in v1."""


class CurvilinearDomain(Domain):
    """Declared seam: non-separable geometry (radar slice, satellite swath). Not built in v1."""
