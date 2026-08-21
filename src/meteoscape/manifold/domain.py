"""`Domain` - the coordinate set over the 4 axes (3 spatial + `valid_time`), and its v1 grid
representation.

Representations vary behind one interface: separability is a *facet* (not the base type) and
regularity is a per-axis choice (`RegularAxis` computes cells from `(anchor, step, count)`), so a
curvilinear geometry can satisfy the base without either. `issue_time` is a provenance stamp, **not**
an axis. v1 ships `GridDomain` (the enumerable grid — mixed `EnumerableAxis` per axis),
`FootprintDomain` (a continuous provider footprint), `SelectionDomain` (the request-side form, which
may carry bounds-only members), and `ScatterDomain` (paired points, jointly matched); `ground`
resolves a request against an enumerable answer.
`CurvilinearDomain` and `intersect` are declared seams.

See ADR-0002.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from math import ceil, floor
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
        if isinstance(self.lower, datetime) != isinstance(other.lower, datetime):
            # Cross-kind pairing escapes the type var where an axis kind is temporal but its *name*
            # is spatial (a snapped X): the two spans occupy different lines, so they never meet.
            return False
        return self.lower <= other.upper and other.lower <= self.upper

    def intersection(self, other: Interval[C]) -> Interval[C] | None:
        """The span both cover - `None` when they do not meet; boundary-touch yields an instant."""
        if not self.intersects(other):
            return None
        return Interval(max(self.lower, other.lower), min(self.upper, other.upper))


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

    Its universal surface is its span (`extent`), request-driven admission (`matches`), and its
    retention sibling (`satisfied_by`) — set-algebra, not enumeration; enumeration is the
    `EnumerableAxis` refinement. An axis is **pure geometry** - it carries no interpolability flag,
    since whether a value may be resampled along it is the parameter's resampler fact, not the
    axis's (ADR-0002).
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

    def satisfied_by(self, held: Axis, needed: Axis) -> bool:
        """Whether `held` answers `needed` as completely as I will ever answer it (ADR-0002).

        Admission's sibling, dispatched on the declaration rather than the request. Default — a
        static axis does not move, so a Holding is a slice of something larger and a wider ask is
        genuinely unanswered until more is fetched.

        `needed` must be bounded: an `ANY` member has no extent, and the caller skips the check
        entirely in that case rather than passing one here.
        """
        want = needed.extent.intersection(self.extent)  # type: ignore[arg-type]
        return want is None or held.extent.contains(want)

    @abstractmethod
    def clip(self, bounds: Interval | None) -> Axis | None:
        """The part of me within `bounds` — all of me when there are none, `None` when we
        do not meet.

        Pure axis algebra: what comes back is whatever the restriction leaves - a span stays a span, a
        lattice stays a lattice at its own phase, a clock-relative window materializes. Needing *cells*
        is a property of `ground`, so the caller that needs them checks, never this (ADR-0002).
        """
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

    def clip(self, bounds: Interval | None) -> RegularAxis | None:
        if bounds is None:
            return self
        # One expression for both coordinate kinds: subtracting coordinates gives a step-like
        # quantity, and dividing by the step gives a plain float either way (concern #23). The
        # tolerance rides that dimensionless quotient, so a bound float-noise off a cell edge
        # clips into the containing cell.
        low = (bounds.lower - self.anchor) / self.step  # type: ignore[operator]
        # A cellular tick owns the span that follows it, so a bound inside a cell keeps that cell;
        # an instant tick is kept only when the bounds reach the tick itself.
        first = max(
            0,
            floor(low + LATTICE_TOLERANCE) if self.cellular else ceil(low - LATTICE_TOLERANCE),
        )
        last = min(
            self.count - 1,
            floor((bounds.upper - self.anchor) / self.step + LATTICE_TOLERANCE),  # type: ignore[operator]
        )
        if first > last:
            return None
        return RegularAxis(
            self.name,
            self.anchor + first * self.step,  # type: ignore[operator]
            self.step,
            last - first + 1,
            self.cellular,
        )

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

    def clip(self, bounds: Interval | None) -> IntervalAxis | None:
        """One cell is never subdivided: it survives whole, or not at all."""
        return self if bounds is None or self.interval.intersects(bounds) else None

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
    """The plain continuous axis: an explicit span, no cells — a `FootprintDomain`'s X/Y footprint.

    The unmarked, static continuous case; the clock-anchored `valid_time` specialization (`RollingAxis`)
    lives with the cadence it reads (`cadence.py`), keeping this module pure geometry. Z footprints use
    `RegularAxis` (point) or `IntervalAxis` (column), not this type.
    """

    name: AxisName
    interval: Interval

    @property
    def extent(self) -> Interval:
        return self.interval

    def clip(self, bounds: Interval | None) -> ContinuousAxis | None:
        """A span restricted is still a span - no cells appear from nowhere."""
        if bounds is None:
            return self
        overlap = self.interval.intersection(bounds)
        return None if overlap is None else ContinuousAxis(self.name, overlap)


@dataclass(frozen=True)
class SnappedAxis(Axis):
    """Bounds-only request axis; without bounds (the default) it is the boundless form (`ANY`) —
    the axis is left entirely to the producer. The resolver's grid supplies anchor and step
    (ADR-0002).

    Intersective `matches` — the span-shaped dual of `VantageAxis`. Bounds are temporal-only
    (`Interval[datetime]`), so a *bounded* float-coordinate member is a type error; the boundless
    member is axis-generic (sits on Z too).
    """

    name: AxisName
    interval: Interval[datetime] | None = None

    def __post_init__(self) -> None:
        if self.interval is None:
            return
        # Bound kind and tz-awareness are invisible to the type system; ordering is a value rule.
        for edge in (self.interval.lower, self.interval.upper):
            if not isinstance(edge, datetime) or edge.tzinfo is None:
                raise ValueError(
                    f"SnappedAxis bounds must be timezone-aware datetimes, got {edge!r}"
                )
        if self.interval.upper < self.interval.lower:
            raise ValueError(
                f"SnappedAxis lower bound {self.interval.lower} exceeds upper {self.interval.upper}"
            )

    @property
    def extent(self) -> Interval:
        if self.interval is None:
            raise ValueError(f"open {self.name.value} member has no extent")
        return self.interval

    def matches(self, declared: Axis) -> bool:
        return self.interval is None or self.interval.intersects(declared.extent)  # type: ignore[arg-type]

    def clip(self, bounds: Interval | None) -> Axis | None:
        # A snapped axis is the bounds another axis is clipped to; it is never asked for a part
        # of itself. Kept total for the `Axis` contract:
        if bounds is None or self.interval is None:
            return self
        overlap = self.interval.intersection(bounds)  # type: ignore[arg-type]
        return None if overlap is None else SnappedAxis(self.name, overlap)


LATTICE_TOLERANCE = 1e-9
"""Index-space (dimensionless) tolerance for float-noise alignment — a fraction of one step, not a
snapping radius. The one policy for every lattice-alignment read (`RegularAxis.clip`,
`sub_lattice_offset`): riding the already-dimensionless coordinate/step quotient keeps it
coordinate-kind-generic (≤ 3.6 µs on an hourly lattice — inert, `timedelta` division is exact)."""

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
    """Start index of `inner`'s anchor on `outer`'s lattice, or `None` when it does not sit on one.

    Requires identical `step`, and `inner.anchor` on the outer lattice within float tolerance
    (time axis uses exact `timedelta` arithmetic — no tolerance). Whether `outer` reaches far enough
    to *cover* `inner` is the caller's question: a lattice that agrees on phase and ends early is a
    countable shortfall, not a misalignment.

    TODO(refactor): split spatial vs temporal `RegularAxis` types so this dispatch is not an
    `isinstance` crawl on the hot path — see concern #23.
    """
    if outer.step != inner.step:
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
        if not isinstance(delta, float) or not isinstance(step, float):
            return None
        quotient = delta / step
        offset = round(quotient)
        if offset < 0 or abs(quotient - offset) > LATTICE_TOLERANCE:
            return None
    return offset


@runtime_checkable
class Separable(Protocol):
    """Facet: per-axis decomposition. A separable representation exposes its axes (enumerable or
    continuous)."""

    def axis(self, name: AxisName) -> Axis: ...


def contains_extents(
    outer: Separable, inner: Separable, z_allowance: Interval | None = None
) -> bool:
    """Whether `outer` whole-box contains `inner` by per-axis extent — **not** `Domain.matches`.

    `matches` is the request-side admission test and `VantageAxis` specialises it to intersection, so
    reusing it would silently make dominance mean "overlaps" (ADR-0007). Both reach consumers — the
    reconciler's domain composition and a Calculator's contained-in-all — read this downward.

    `z_allowance` is a plain band, never a `ParameterDef` — geometry stays parameter-blind. `None`
    is pure containment on Z too.
    """
    return all(
        _extent_contains(outer.axis(name).extent, inner.axis(name).extent, name, z_allowance)
        for name in AXIS_ORDER
    )


def _extent_contains(
    outer: Interval, inner: Interval, name: AxisName, z_allowance: Interval | None
) -> bool:
    if name is AxisName.Z and z_allowance is not None:
        return _sample_z_contains(outer, inner, z_allowance)
    return outer.contains(inner)  # type: ignore[arg-type]


def _sample_z_contains(outer: Interval, inner: Interval, band: Interval) -> bool:
    """Equal levels compose even outside the band — the band licenses, it never constrains (ADR-0007).

    A sample-vs-span pair under a band is a modeling violation: do not absorb it as span-contains-point.
    """
    outer_sample = outer.lower == outer.upper
    inner_sample = inner.lower == inner.upper
    if outer_sample and inner_sample:
        return outer == inner or (band.contains(outer) and band.contains(inner))
    if outer_sample or inner_sample:
        return False
    return outer.contains(inner)  # type: ignore[arg-type]


# TODO: Move operator attribution out of geometry; see concern #46.
def split_extents(
    left_key: object,
    left: Separable,
    right_key: object,
    right: Separable,
    z_allowance: Interval | None = None,
) -> str:
    """Why two Domains fail to nest, **both directions** — the split is the incomparability.

    A single "failing axis" is a misreport: nested-but-incomparable boxes (`Global x 10 d` vs
    `Europe x 16 d`) each dominate on a *different* axis, and naming only the first sends an operator to
    the axis where the other candidate is winning.

    A sample level outside `z_allowance` is not coverage: report the level and the band instead of
    the mutual "extends beyond" pair (ADR-0007).
    """
    parts: list[str] = []
    for name in AXIS_ORDER:
        a = left.axis(name).extent
        b = right.axis(name).extent
        if name is AxisName.Z and z_allowance is not None:
            parts.extend(_sample_z_split(left_key, a, right_key, b, z_allowance))
            continue
        if not a.contains(b):  # type: ignore[arg-type]
            parts.append(f"{right_key} extends beyond {left_key} on {name.value}")
        if not b.contains(a):  # type: ignore[arg-type]
            parts.append(f"{left_key} extends beyond {right_key} on {name.value}")
    return "; ".join(parts)


def _sample_z_split(
    left_key: object,
    left: Interval,
    right_key: object,
    right: Interval,
    band: Interval,
) -> list[str]:
    if _sample_z_contains(left, right, band) and _sample_z_contains(right, left, band):
        return []
    left_sample = left.lower == left.upper
    right_sample = right.lower == right.upper
    if left_sample and right_sample:
        return [
            f"z level {extent.lower} outside allowance [{band.lower}, {band.upper}]"
            for extent in (left, right)
            if not band.contains(extent)
        ]
    parts: list[str] = []
    if not _sample_z_contains(left, right, band):
        parts.append(f"{right_key} extends beyond {left_key} on z")
    if not _sample_z_contains(right, left, band):
        parts.append(f"{left_key} extends beyond {right_key} on z")
    return parts


def first_incomparable(
    candidates: Sequence[tuple[object, Separable]],
    z_allowance: Interval | None = None,
) -> tuple[tuple[object, Separable], tuple[object, Separable]] | None:
    """First pair nesting neither way — the witness both call sites report when selection is unresolved."""
    for i, left in enumerate(candidates):
        for right in candidates[i + 1 :]:
            if not contains_extents(
                left[1], right[1], z_allowance=z_allowance
            ) and not contains_extents(right[1], left[1], z_allowance=z_allowance):
                return left, right
    return None


def _admits_per_axis(declared: Mapping[AxisName, Axis], requested: Domain) -> bool:
    """The declared-side admission fold every separable representation shares.

    Total the way `Domain.matches` must be: a non-separable request is a survivable `False`, never a
    crash, so an unknown representation skips a candidate instead of failing the loop (ADR-0002).
    """
    if not isinstance(requested, Separable):
        return False
    return all(requested.axis(name).matches(declared[name]) for name in AXIS_ORDER)


def as_separable(domain: Domain) -> Separable | None:
    """The domain as `Separable`, or `None` — pure geometry, no error text, no producer key.

    Returns rather than raises so each caller stays the sole author of its `CompositionError`, with
    its own context — the reconciler names the parameter, the Calculator node its key — rather
    than dressing up a generic geometry error (ADR-0007).
    """
    return domain if isinstance(domain, Separable) else None


def as_enumerable_axes(domain: Domain) -> Mapping[AxisName, EnumerableAxis] | None:
    """The domain's four axes, all enumerable — or `None` when any of them is not.

    `as_separable`'s cell-bearing sibling: separability says *decomposable per axis*, this says
    *and every part has cells*. Returns rather than raises, on the same grounds — a caller that
    needs coordinates (a crop target, a read-back address) owns the sentence for why it needed them.
    """
    separable = as_separable(domain)
    if separable is None:
        return None
    axes: dict[AxisName, EnumerableAxis] = {}
    for name in AXIS_ORDER:
        member = separable.axis(name)
        if not isinstance(member, EnumerableAxis):
            return None
        axes[name] = member
    return axes


class Domain(ABC):
    """An abstract coordinate set over the 4 axes - continuous or enumerable.

    Only the set-algebra (`matches` / `intersect`) is universal; enumeration is the `EnumerableDomain`
    refinement, so *being* one is the enumerability discriminator (ADR-0002). Resolution is **not**
    universal - being a *request* is a property of some domains only, so `ground` is a function.
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
        return _admits_per_axis(self.axes, other)

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

    def axis(self, name: AxisName) -> EnumerableAxis:
        # Narrower than `Separable.axis` by construction — every `GridDomain` axis is enumerable.
        return self.axes[name]


@dataclass(frozen=True)
class FootprintDomain(Domain):
    """A producer's declared footprint - a **non-enumerable**, `Separable` region, the geometry the
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
        return _admits_per_axis(self.axes, other)

    def intersect(self, other: Domain) -> Domain:
        raise NotImplementedError

    def axis(self, name: AxisName) -> Axis:
        return self.axes[name]


@dataclass(frozen=True)
class ScatterDomain(Domain):
    """Finite paired X/Y points matched jointly, sharing T and Z.

    X/Y are never an axis product: a request is admitted only at a member place, exactly
    (no epsilon). Boundless (`ANY`) and boxed spatial asks decline — "all stations" waits on
    a scatter-shaped Coverage (#12). Not Separable: exposing `axis()` would falsely pass
    `as_separable` and make per-axis composition appear valid. `points` order does not affect
    admission but does affect equality, and becomes the positional order of the Coverage a
    scatter will one day carry. ADR-0002; glossary ScatterDomain.
    """

    points: tuple[tuple[float, float], ...]
    t: Axis
    z: Axis

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError(
                "an empty scatter is capability absence, not a domain that declines everything"
            )
        if len(self.points) != len(set(self.points)):
            raise ValueError("duplicate scatter points; a registry lists a place once")

    def matches(self, other: Domain) -> bool:
        requested = as_separable(other)
        if requested is None:
            return False
        place = _request_place(requested)
        return (
            place is not None
            and place in self.points
            and requested.axis(AxisName.T).matches(self.t)
            and requested.axis(AxisName.Z).matches(self.z)
        )

    def intersect(self, other: Domain) -> Domain:
        raise NotImplementedError


def _request_place(requested: Separable) -> tuple[float, float] | None:
    """The request's X/Y as one place, or `None` when it is not a single point."""
    x = _point_coordinate(requested.axis(AxisName.X))
    y = _point_coordinate(requested.axis(AxisName.Y))
    if x is None or y is None:
        return None
    return (x, y)


def _point_coordinate(axis: Axis) -> float | None:
    """A single-cell instant's float coordinate, or `None` for a span, `ANY`, or a non-point."""
    if not isinstance(axis, EnumerableAxis) or len(axis) != 1:
        return None
    if axis.extent.lower != axis.extent.upper:
        return None
    coordinate = axis[0].coordinate
    return coordinate if isinstance(coordinate, float) else None


type SelectableAxis = RegularAxis | VantageAxis | SnappedAxis


@dataclass(frozen=True)
class SelectionDomain(Domain):
    """The request-side representation: one `SelectableAxis` per axis, so a member may state bounds only.

    `Separable` structurally but never `Enumerable` — it has no cells until `ground` resolves it, and
    nothing narrows to it nominally (`Selection.domain` stays base `Domain`), so a `GridDomain` remains
    an equally legal request. See ADR-0002.
    """

    axes: Mapping[AxisName, SelectableAxis]

    def __post_init__(self) -> None:
        _validate_four_axes(self.axes)

    def matches(self, other: Domain) -> bool:
        return _admits_per_axis(self.axes, other)

    def intersect(self, other: Domain) -> Domain:
        raise NotImplementedError

    def axis(self, name: AxisName) -> SelectableAxis:
        return self.axes[name]


def ground(request: Domain, against: Domain) -> EnumerableDomain:
    """The answer geometry `request` asks for, resolved against `against`'s geometry.

    ADR-0001's shape-correspondence as one operation: pinned members pass through by identity, a
    snapped member takes what the answering axis clips itself to. The answering read is per-axis and
    happens only for snapped members, so a fully pinned request resolves against *anything* - identity
    reads nothing.

    Deliberately a function rather than a `Domain` method, so that no caller holding a base `Domain`
    has to branch on representation to learn whether resolution is needed; it becomes a method when the
    request side narrows to one representation (ADR-0002, concern #42).

    `ValueError` when a member cannot resolve: *why* that matters is the caller's knowledge, not this
    layer's - a vendor answering a foreign window and a mis-quantized store are different failures.
    """
    if isinstance(request, EnumerableDomain):
        return request  # an exact request is already its own answer
    if not isinstance(request, SelectionDomain):
        raise ValueError(f"{type(request).__name__} is a declared geometry, not a request")

    answering = as_separable(against)
    axes: dict[AxisName, EnumerableAxis] = {}
    for name in AXIS_ORDER:
        member = request.axes[name]
        if not isinstance(member, SnappedAxis):
            axes[name] = member
            continue
        if answering is None:
            raise ValueError(f"a snapped {name.value} grounds only against separable geometry")
        # No bounds → the axis entire (ANY); one clock read on a RollingAxis, never two.
        part = answering.axis(name).clip(member.interval)
        if part is None:
            raise ValueError(f"no {name.value} within the requested bounds")
        if not isinstance(part, EnumerableAxis):
            # Grounding is what needs cells — a declared span has none to snap to.
            raise ValueError(
                f"a snapped {name.value} needs cells; the answering {name.value} is a span"
            )
        axes[name] = part
    return GridDomain(axes=axes)


def open_axes(domain: Domain) -> frozenset[AxisName]:
    """The axes a request leaves entirely to the producer — empty for anything but a Selection.

    The single reading of boundlessness: it licenses differing resolutions in `agreed_geometry` and
    tells a producer its answer may keep its native shape. Both read it here rather than inspecting
    request representation themselves, which is what keeps *what the ask left open* one fact.

    The empty answer for every other representation is **silent by construction**, and that is the
    risk worth naming rather than the convenience: a second request representation carrying a
    boundless member would lose its licence here with nothing raised and nothing logged — the fold
    would then raise on a difference the request had actually granted. `SelectionDomain` is the only
    request representation minted, so the arm is total today; whichever representation wins in
    concern #42 has to be added here first.
    """
    if not isinstance(domain, SelectionDomain):
        return frozenset()
    return frozenset(
        name
        for name in AXIS_ORDER
        if isinstance(member := domain.axes[name], SnappedAxis) and member.interval is None
    )


def agreed_geometry(grounded: Iterable[EnumerableDomain], *, request: Domain) -> EnumerableDomain:
    """The one geometry a set of resolutions agree to answer `request` with.

    ADR-0002's fold rule: resolutions must be equal on every axis the request does not leave
    entirely to the producer; the first disagreement raises naming the axis, and an empty input
    raises. On open axes resolutions may differ — records keep their own domains, so the fold
    validates the licence and returns the **first** resolution, authoritative on every bounded
    axis. The licence (`open_axes`) is derived here — a fact of the request, never a caller's
    claim.

    Duplicates fold on whole equality, so only *distinct* resolutions must expose axes
    (`Separable`); an agreeing non-separable resolution passes (concern #12's target role).
    """
    boundless = open_axes(request)
    members: list[EnumerableDomain] = []
    for resolution in grounded:
        if resolution in members:
            continue
        if members:
            reference, novel = as_separable(members[0]), as_separable(resolution)
            if reference is None or novel is None:
                raise ValueError("distinct resolutions need axes to license their difference")
            for name in AXIS_ORDER:
                if name not in boundless and reference.axis(name) != novel.axis(name):
                    raise ValueError(f"resolutions disagree on {name.value}")
        members.append(resolution)
    if not members:
        raise ValueError("no geometry to agree on")
    return members[0]


class CurvilinearDomain(Domain):
    """Declared seam: non-separable geometry (radar slice, satellite swath). Not built in v1."""
