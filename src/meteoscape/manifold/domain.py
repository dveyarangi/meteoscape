"""`Domain` - the coordinate set over the 4 axes (3 spatial + `valid_time`), and its v1 grid
representation.

Representations vary behind one interface: separability is a *facet* (not the base type) and
regularity is a per-axis choice (`RegularAxis` computes cells from `(anchor, step, count)`), so a
curvilinear geometry can satisfy the base without either. `issue_time` is a provenance stamp, **not**
an axis. v1 ships `GridDomain` (the enumerable grid — mixed `EnumerableAxis` per axis) and
`FootprintDomain` (a continuous provider reach); `CurvilinearDomain` and `intersect` are declared seams.

See ADR-0002.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
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
    T = "t"  # valid_time


@dataclass(frozen=True)
class Interval[C: (float, datetime)]:
    """A span on one axis (`lower`..`upper`) - a `Cell`'s bounds, and an `Axis`'s `extent`.

    Generic over the axis's coordinate type (a *constrained* type var: `float` **or** `datetime`, never
    the `Coordinate` union), so an interval's two bounds are provably the same comparable type and
    `contains` / `intersects` type-check - a spatial interval can't be compared against a time one.
    """

    lower: C
    upper: C

    def contains(self, other: Interval[C]) -> bool:
        return self.lower <= other.lower and other.upper <= self.upper

    def intersects(self, other: Interval[C]) -> bool:
        return self.lower <= other.upper and other.lower <= self.upper


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

    Its universal surface is its span (`extent`) plus request-driven admission (`matches`) — set-
    algebra, not enumeration; enumeration is the `EnumerableAxis` refinement. An axis is **pure
    geometry** - it carries no interpolability flag, since whether a value may be resampled along it
    is the parameter's resampler fact, not the axis's (ADR-0002).
    """

    name: AxisName

    @property
    @abstractmethod
    def extent(self) -> Interval:
        """The axis's span (for a `RollingAxis`, resolved against its clock at read)."""
        ...

    def matches(self, declared: Axis) -> bool:
        """Whether this *requested* axis matches a *declared* axis — default: full containment."""
        return declared.extent.contains(self.extent)  # type: ignore[arg-type]


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
    encoded in `anchor`. Absence is never meaningful — a point is `count=1`; `step` always advances.
    """

    name: AxisName
    anchor: Coordinate
    step: Step
    count: int
    cellular: bool

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError(f"RegularAxis.count must be >= 1, got {self.count}")
        if isinstance(self.step, timedelta):
            if self.step <= timedelta(0):
                raise ValueError(f"RegularAxis.step must be > 0, got {self.step}")
        elif self.step <= 0:
            raise ValueError(f"RegularAxis.step must be > 0, got {self.step}")

    @property
    def extent(self) -> Interval:
        # Tick span — cellular only affects Cell.bounds, never axis geometry.
        upper = self.anchor + self.step * (self.count - 1)  # type: ignore[operator]
        return Interval(self.anchor, upper)  # type: ignore[arg-type]

    def __getitem__(self, index: int) -> Cell:
        if not 0 <= index < self.count:
            raise IndexError(index)
        coordinate = self.anchor + self.step * index  # type: ignore[operator]
        bounds = (
            Interval(coordinate, coordinate + self.step)  # type: ignore[operator, arg-type]
            if self.cellular
            else None
        )
        return Cell(coordinate, bounds)

    def __len__(self) -> int:
        return self.count


@dataclass(frozen=True)
class IntervalAxis(EnumerableAxis):
    """A single enumerable cell defined by an `interval` — `extent` is the interval itself.

    The enumerable encoding of a span cell (e.g. a native cloud column `[0, TOA]`). Inherits the
    default containment `matches`; `VantageAxis` specialises with intersection.
    """

    name: AxisName
    interval: Interval

    @property
    def extent(self) -> Interval:
        return self.interval

    def __getitem__(self, index: int) -> Cell:
        if index != 0:
            raise IndexError(index)
        return Cell(self.interval.lower, self.interval)

    def __len__(self) -> int:
        return 1


@dataclass(frozen=True)
class VantageAxis(IntervalAxis):
    """A single-cell observation aperture: admits any declared axis whose extent intersects it.

    Lives on the Selection (and rides onto the Coverage by closed projection). Never a capability
    footprint axis — providers declare native Z as a `RegularAxis` point or `IntervalAxis` column.
    """

    def matches(self, declared: Axis) -> bool:
        return self.interval.intersects(declared.extent)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ContinuousAxis(Axis):
    """The plain continuous axis: an explicit span, no cells — a `FootprintDomain`'s X/Y reach.

    The unmarked, static continuous case; the clock-anchored `valid_time` specialization (`RollingAxis`)
    lives with the cadence it reads (`cadence.py`), keeping this module pure geometry. Z footprints use
    `RegularAxis` (point) or `IntervalAxis` (column), not this type.
    """

    name: AxisName
    interval: Interval

    @property
    def extent(self) -> Interval:
        return self.interval


LATTICE_TOLERANCE = 1e-9
"""Absolute spatial tolerance (degrees) for float-noise alignment — not a snapping radius."""

AXIS_ORDER: tuple[AxisName, ...] = (AxisName.X, AxisName.Y, AxisName.Z, AxisName.T)
"""Canonical nesting order: X → Y → Z → T, T fastest-varying (row-major)."""

_REQUIRED_AXES = frozenset(AXIS_ORDER)


def _validate_four_axes(axes: Mapping[AxisName, Axis]) -> None:
    """Exactly the four field axes, each keyed by its own `name`."""
    if set(axes) != _REQUIRED_AXES:
        raise ValueError(f"Domain requires exactly the four axes {_REQUIRED_AXES}, got {set(axes)}")
    for name, axis in axes.items():
        if axis.name is not name:
            raise ValueError(f"axis key {name} does not match axis.name {axis.name}")


def encode_flat_index(axis_counts: Mapping[AxisName, int], locals_: Mapping[AxisName, int]) -> int:
    """Encode per-axis indices into a flat row-major index (T fastest — `AXIS_ORDER`)."""
    index = 0
    for name in AXIS_ORDER:
        index = index * axis_counts[name] + locals_[name]
    return index


def decode_flat_index(axis_counts: Mapping[AxisName, int], index: int) -> dict[AxisName, int]:
    """Decode a flat row-major index into per-axis locals (T fastest — `AXIS_ORDER`)."""
    locals_: dict[AxisName, int] = {}
    remainder = index
    for name in reversed(AXIS_ORDER):
        remainder, local = divmod(remainder, axis_counts[name])
        locals_[name] = local
    return locals_


def sub_lattice_offset(outer: RegularAxis, inner: RegularAxis) -> int | None:
    """Start index of `inner` within `outer`, or `None` if off-phase / incompatible.

    Requires identical `step`, and `inner.anchor` on the outer lattice within float tolerance
    (time axis uses exact `timedelta` arithmetic — no tolerance).

    TODO(refactor): split spatial vs temporal `RegularAxis` types so this dispatch is not an
    `isinstance` crawl on the hot path — see concern #23.
    """
    if outer.step != inner.step or inner.count > outer.count:
        return None
    delta = inner.anchor - outer.anchor  # type: ignore[operator]
    step = outer.step
    if isinstance(step, timedelta):
        if not isinstance(delta, timedelta) or delta < timedelta(0):
            return None
        quot, rem = divmod(delta, step)
        if rem != timedelta(0):
            return None
        offset = int(quot)
    else:
        if (
            not isinstance(delta, float)
            or not isinstance(step, float)
            or not isinstance(outer.anchor, float)
            or not isinstance(inner.anchor, float)
        ):
            return None
        raw = delta / step
        offset = round(raw)
        if offset < 0:
            return None
        aligned = outer.anchor + step * offset
        if abs(inner.anchor - aligned) > LATTICE_TOLERANCE:
            return None
    if offset + inner.count > outer.count:
        return None
    return offset


@runtime_checkable
class Separable(Protocol):
    """Facet: per-axis decomposition. A separable representation exposes its axes (enumerable or
    continuous)."""

    def axis(self, name: AxisName) -> Axis: ...


class Domain(ABC):
    """An abstract coordinate set over the 4 axes - continuous or enumerable.

    Only the set-algebra (`matches` / `intersect`) is universal; enumeration is the `EnumerableDomain`
    refinement, so *being* one is the enumerability discriminator (ADR-0002).
    """

    @abstractmethod
    def matches(self, other: Domain) -> bool:
        """Whether this *declared* domain matches a *requested* `other` — per-axis `matches`."""
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
class GridDomain(EnumerableDomain):
    """The v1 enumerable-grid representation: an `EnumerableAxis` per axis (mixed kinds allowed).

    Separable (exposes its axes). Index math uses only `len` / `[]`, so a `VantageAxis` or
    `IntervalAxis` on Z needs no new arithmetic. Regularity rides on the axes that are `RegularAxis`.
    """

    axes: Mapping[AxisName, EnumerableAxis]
    _size: int = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate_four_axes(self.axes)
        size = 1
        for name in AXIS_ORDER:
            size *= len(self.axes[name])
        object.__setattr__(self, "_size", size)

    def matches(self, other: Domain) -> bool:
        if not isinstance(other, Separable):
            return False
        return all(other.axis(name).matches(self.axes[name]) for name in AXIS_ORDER)

    def intersect(self, other: Domain) -> Domain:
        raise NotImplementedError

    def enumerate(self) -> Iterator[Point]:
        return (self[i] for i in range(len(self)))

    def __getitem__(self, index: int) -> Point:
        if not 0 <= index < len(self):
            raise IndexError(index)
        counts = {name: len(self.axes[name]) for name in AXIS_ORDER}
        locals_ = decode_flat_index(counts, index)
        return Point({name: self.axes[name][locals_[name]] for name in AXIS_ORDER})

    def __len__(self) -> int:
        return self._size

    def axis(self, name: AxisName) -> Axis:
        return self.axes[name]


@dataclass(frozen=True)
class FootprintDomain(Domain):
    """A producer's declared reach - a **non-enumerable**, `Separable` region, the footprint the
    Capability filter tests against.

    Per-axis bounds: typically a `ContinuousAxis` on X/Y, a `RegularAxis` point or `IntervalAxis`
    column on Z, and a clock-anchored `RollingAxis` on `valid_time`. `matches` composes **per-axis
    `matches`** (request-driven); its `RollingAxis` makes it clock-relative, so admission tracks the
    provider's rolling horizon while `serves` stays a plain `matches`.
    """

    axes: Mapping[AxisName, Axis]

    def __post_init__(self) -> None:
        _validate_four_axes(self.axes)

    def matches(self, other: Domain) -> bool:
        if not isinstance(other, Separable):
            return False
        return all(other.axis(name).matches(self.axes[name]) for name in AXIS_ORDER)

    def intersect(self, other: Domain) -> Domain:
        raise NotImplementedError

    def axis(self, name: AxisName) -> Axis:
        return self.axes[name]


class CurvilinearDomain(Domain):
    """Declared seam: non-separable geometry (radar slice, satellite swath). Not built in v1."""
