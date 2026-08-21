"""Point+timeline provider family — one algebra, members that differ in geometry.

A timeline producer delivers a single X/Y point and a regular T series; only Z varies per parameter.
`TimelineProvider` holds every algebraic step; a member answers where it lives, how a request grounds,
how it signs, and how it refreshes fetched facts. The vendor arrives as an injected `TimelineProbe`.
A genuinely new delivery shape (gridded NWP, a swath) adds a wrapper beside this family, never a Probe.

The contract both halves answer to is docs/edge/provider.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol, runtime_checkable

from ...clock import Clock
from ...errors import CapabilityMismatch, RuntimeFailure
from ...identity import SourceKey
from ...manifold.cadence import CadenceDef, RollingAxis
from ...manifold.capability import EnumerableCapability, GranularCapability
from ...manifold.core import Manifold, Selection
from ...manifold.coverage import CoverageRecord, CoverageSet
from ...manifold.data import ParameterData
from ...manifold.domain import (
    AxisName,
    ContinuousAxis,
    Domain,
    FootprintDomain,
    GridDomain,
    Interval,
    IntervalAxis,
    RegularAxis,
    agreed_geometry,
    ground,
    open_axes,
)
from ...manifold.provenance import AtomicOrigin, Provenance, Uniform
from ...manifold.sampling import Shortfall
from ...parameters import ParameterDef, ParameterId
from ..catalog.paramtable import ParameterTable
from .base import Provider
from .normalization import kmh_to_ms

GLOBAL_LONGITUDES = Interval(-180.0, 180.0)
GLOBAL_LATITUDES = Interval(-90.0, 90.0)
"""The whole-globe reach a worldwide point API declares by saying nothing; a regional one overrides."""


class TimelineProvider(Provider, ABC):
    """The point-plus-series algebra — fetch, interpret, tick check, grid build, crop.

    A member contributes the geometry it publishes, how a request grounds onto it, how an answer
    is signed, and an await-able refresh that a producer with fixed facts does nothing in.
    Cadence, clock, and spatial reach are one member's facts.
    """

    def __init__(
        self,
        *,
        probe: TimelineProbe,
        taps: TapTable,
        step: timedelta,
        parameters: ParameterTable,
        source_key: SourceKey,
    ) -> None:
        self._probe = probe
        self._taps = taps
        self._step = step
        self._parameters = parameters
        self._source_key = source_key
        self._source = source_key.provider

    async def project(self, selection: Selection) -> Manifold:
        """One vendor call, answered either at the geometry the ask pinned or at this producer's own.

        Anything unservable is settled before the wire. The branch below reads one derived fact —
        `open_axes`, the axes the ask left entirely to the producer: where there are any, the answer
        keeps its native cells *and* the whole fetch unit they arrived in; where there are none, it is
        cropped to exactly what was named. No snap arithmetic and no request-shape gate live here.
        """
        if not selection.parameters:
            raise CapabilityMismatch(f"{self._source} Selection requests no served parameters")
        unserved = selection.parameters - self._taps.parameters
        if unserved:
            raise CapabilityMismatch(f"{self._source} does not serve {sorted(unserved)}")
        boundless = open_axes(selection.domain)
        # One Probe call whatever the tap count, so the whole table is the natural fetch unit here.
        engaged = self._taps if boundless else self._taps.engaged_by(selection.parameters)
        # Refresh after the parameter guards so an unservable ask never buys I/O, and before
        # resolve so grounding reads facts the refresh just settled.
        await self.refresh()
        wanted = self.resolve(selection.domain, self._engaged_ids(engaged))
        longitude, latitude = self._point_of(wanted)
        delivery = await self._probe.retrieve(
            longitude=longitude,
            latitude=latitude,
            over=self._window_of(wanted),
            variables=engaged.variables,
        )
        # No empty-records guard, and the silence is deliberate: the guards above leave `engaged`
        # non-empty, `by_level()` yields a group per engaged tap, and `interpret` values every one or
        # raises — so an empty delivery cannot arrive here. It is unasserted rather than unreachable
        # by luck; if a later shape makes it reachable it needs its own `RuntimeFailure`, because the
        # fold below would report a vendor returning nothing as `CapabilityMismatch`.
        # Stamp after retrieve: today's interpret-time clock read. Stamping first would move
        # fetched_at / expiration by retrieve latency.
        records = self._interpret(
            delivery,
            engaged,
            longitude=longitude,
            latitude=latitude,
            provenance=Uniform(self.stamp(wanted)),
        )
        answer = self._answered_geometry(records, selection)
        group = CoverageSet(tuple(records))
        if boundless:
            return group
        return await self._delivered(group, answer, selection.parameters)

    @property
    def source_key(self) -> SourceKey:
        return self._source_key

    async def refresh(self) -> None:
        """Bring fetched facts up to date. Fixed-facts members inherit this no-op."""

    @abstractmethod
    def resolve(self, request: Domain, parameters: Sequence[ParameterId]) -> GridDomain:
        """The geometry this producer answers `request` with — its own `ground` call(s).

        `parameters` arrives deduped in declaration order.
        """

    @abstractmethod
    def stamp(self, wanted: GridDomain) -> Provenance:
        """The origin plane for one fetch, given the geometry resolved for it."""

    def _engaged_ids(self, taps: TapTable) -> tuple[ParameterId, ...]:
        """Declaration order, each parameter once — `agreed_geometry` returns `members[0]`."""
        return tuple(dict.fromkeys(tap.produces for tap in taps))

    # --- Resolution: the point and window the vendor face is handed ---

    def _point_of(self, wanted: GridDomain) -> tuple[float, float]:
        """The one point the timeline is drawn at, as the vendor face takes it."""
        longitude = wanted.axis(AxisName.X).extent.lower
        latitude = wanted.axis(AxisName.Y).extent.lower
        if not isinstance(longitude, float) or not isinstance(latitude, float):
            raise RuntimeFailure(f"{self._source} resolved X/Y must be spatial floats")
        return longitude, latitude

    def _window_of(self, wanted: GridDomain) -> Interval[datetime]:
        """The span to ask over — the resolved lattice's own edges, with no arithmetic left to do.

        The clamp to the live window, the floor of both bounds onto this producer's ticks,
        end-inclusivity, and the raced-empty decline are all one `clip` inside `ground`.

        Reading the window off a single resolution is sound only because this family answers with
        **one** T on every footprint — including a boundless T, which every footprint grounds into
        the same window. A shape carrying per-parameter windows loses that guarantee and must fold
        its own window here.
        """
        span = wanted.axis(AxisName.T).extent
        if not isinstance(span.lower, datetime) or not isinstance(span.upper, datetime):
            raise RuntimeFailure(f"{self._source} resolved T must be datetime")
        return Interval(span.lower, span.upper)

    # --- Interpretation: the delivery as native records ---

    def _interpret(
        self,
        delivery: TimelineDelivery,
        taps: TapTable,
        *,
        longitude: float,
        latitude: float,
        provenance: Uniform,
    ) -> Sequence[CoverageRecord]:
        """The vendor's account as native records: canonical values on the geometry delivered.

        One record per Z cell (ADR-0006) — every parameter's values are positional to the delivered
        ticks alone, so what groups them is the only axis that varies. X/Y are the point asked at: a
        vendor echoing its own snapped cell centre is answering a question resolution already settled.
        """
        if self._probe.reports_units and delivery.reported_units is None:
            raise RuntimeFailure(f"{self._source} declares reported units but delivered none")
        values = taps.interpret(delivery, source=self._source)
        valid_time = self._lattice_of(delivery.valid_time)
        records: list[CoverageRecord] = []
        for z_spec, group in taps.by_level().items():
            domain = GridDomain(
                axes={
                    AxisName.X: RegularAxis(AxisName.X, longitude, 1.0, 1, False),
                    AxisName.Y: RegularAxis(AxisName.Y, latitude, 1.0, 1, False),
                    AxisName.Z: axis(z_spec),
                    AxisName.T: valid_time,
                }
            )
            records.append(
                CoverageRecord(
                    capability=EnumerableCapability(
                        domain=domain,
                        parameters={
                            tap.produces: self._parameters.get(tap.produces) for tap in group
                        },
                    ),
                    ranges={tap.produces: values[tap.produces] for tap in group},
                    provenance=provenance,
                )
            )
        return records

    def _lattice_of(self, ticks: Sequence[datetime]) -> RegularAxis:
        """The delivered stamps as an axis — derived, then held against the *declared* step.

        This is what turns "the delivery matches the declaration" from a promise into a computation:
        a producer whose series lands off its own step would otherwise ground to one lattice and be
        indexed on another, so it fails here instead.
        """
        if not ticks:
            raise RuntimeFailure(f"{self._source} delivered an empty series")
        for i, tick in enumerate(ticks):
            if tick != ticks[0] + self._step * i:
                raise RuntimeFailure(f"{self._source} delivered a series off its declared step")
        return RegularAxis(AxisName.T, ticks[0], self._step, len(ticks), True)

    # --- The answer: the geometry this fetch answers with, and the fold onto it ---

    def _answered_geometry(
        self, records: Sequence[CoverageRecord], selection: Selection
    ) -> GridDomain:
        """The geometry this fetch answers with: the request, resolved against every record delivered.

        Its **raising** arm is a law, not a live guard here — do not read it as one: this shape stamps
        one derived lattice onto every record, so on a bounded axis its records cannot disagree. It is
        kept because a shape deriving a lattice *per record* would need it, and because divergence
        between the two fetches of one request is the **Arbiter's** to catch, never this.

        On an axis the ask left open, records legitimately differ and the fold validates that instead
        of firing; what it returns is then read only where the answer is cropped.
        """
        try:
            answer = agreed_geometry(
                (ground(selection.domain, record.domain) for record in records),
                request=selection.domain,
            )
        except ValueError as exc:
            raise CapabilityMismatch(f"{self._source} cannot answer this selection: {exc}") from exc
        # The answer of a grounded request is a grid; the crop reads it per axis.
        assert isinstance(answer, GridDomain)
        return answer

    async def _delivered(
        self, group: CoverageSet, answer: GridDomain, parameters: frozenset[ParameterId]
    ) -> Manifold:
        """The fetch folded onto the answer — and this wrapper's whole fault boundary.

        The vendor is the authority on what exists and the request on what is in bounds, which is why
        a wider delivery is trimmed rather than refused. A `Shortfall` can only come from an **exact**
        request: a snapped answer is grounded against the delivery, so there is nothing for it to fall
        short of. It means the caller's own coordinates went unanswered — aligned, short by a known
        count, and a fault rather than an unservable request.

        **TODO (temporary):** this translation goes with the raise it catches, once a short tail is
        padded as `present=False`
        (docs/concerns.md#30-response-membership-under-runtime-degraded-fallback).
        """
        try:
            return await group.project(Selection(domain=answer, parameters=parameters))
        except Shortfall as exc:
            raise RuntimeFailure(f"{self._source} delivered less than it declared: {exc}") from exc


class RollingTimeline(TimelineProvider):
    """A continuous footprint whose window rides the clock forward.

    Open-Meteo and TWC are this member: whole-plane reach, rolling cadence, run-stamped provenance.
    Constructor arguments are **per-offering** facts, carrying one offering's worth in v1
    (docs/concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection).
    """

    def __init__(
        self,
        *,
        probe: TimelineProbe,
        taps: TapTable,
        step: timedelta,
        cadence: CadenceDef,
        clock: Clock,
        parameters: ParameterTable,
        source_key: SourceKey,
        longitudes: Interval[float] = GLOBAL_LONGITUDES,
        latitudes: Interval[float] = GLOBAL_LATITUDES,
    ) -> None:
        super().__init__(
            probe=probe,
            taps=taps,
            step=step,
            parameters=parameters,
            source_key=source_key,
        )
        self._cadence = cadence
        self._clock = clock
        self._footprints = _declare_footprints(
            taps,
            step=step,
            cadence=cadence,
            clock=clock,
            parameters=parameters,
            longitudes=longitudes,
            latitudes=latitudes,
        )
        self._capability = GranularCapability(reaches=self._footprints)

    @property
    def capability(self) -> GranularCapability:
        return self._capability

    def resolve(self, request: Domain, parameters: Sequence[ParameterId]) -> GridDomain:
        """The pre-fetch `ground`: what this producer's own declared geometry answers the request with.

        One fetch carries one geometry on every bounded axis; boundless axes license per-footprint
        difference, which the fold validates while answering the bounded shape.
        """
        try:
            wanted = agreed_geometry(
                (ground(request, self._footprints[parameter][1]) for parameter in parameters),
                request=request,
            )
        except ValueError as exc:
            raise CapabilityMismatch(f"{self._source} cannot serve this selection: {exc}") from exc
        # `ground` builds a grid; v1 mints no other enumerable representation.
        assert isinstance(wanted, GridDomain)
        return wanted

    def stamp(self, wanted: GridDomain) -> Provenance:
        """One fetch, one plane: the run this answer came from, and when it goes stale (ADR-0003).

        The resolved place is the scatter member's to name; a rolling run reads the clock.
        """
        del wanted
        now = self._clock.now()
        return Provenance(
            origin=AtomicOrigin(self._source_key, self._cadence.anchor(now)),
            fetched_at=now,
            expiration=self._cadence.expiration(now),
        )


def _declare_footprints(
    taps: TapTable,
    *,
    step: timedelta,
    cadence: CadenceDef,
    clock: Clock,
    parameters: ParameterTable,
    longitudes: Interval[float],
    latitudes: Interval[float],
) -> Mapping[ParameterId, tuple[ParameterDef, FootprintDomain]]:
    """The producer's own geometry, at its concrete type: a point field over a rolling series.

    The `Capability` widens these to `Domain` — it is the abstract advertisement, and a producer
    declaring curvilinear geometry advertises through the same field
    (#12 in docs/concerns.md, source role). The rolling member keeps the narrow map because it
    *knows* what it built, and resolution reads it back at that type.
    """
    footprints: dict[ParameterId, tuple[ParameterDef, FootprintDomain]] = {}
    xy_t = {
        AxisName.X: ContinuousAxis(AxisName.X, longitudes),
        AxisName.Y: ContinuousAxis(AxisName.Y, latitudes),
        AxisName.T: RollingAxis(AxisName.T, cadence, clock, step),
    }
    for tap in taps:
        footprints[tap.produces] = (
            parameters.get(tap.produces),
            FootprintDomain(axes={**xy_t, AxisName.Z: axis(tap.z)}),
        )
    return footprints


# --- The vendor seam ---


@runtime_checkable
class TimelineProbe(Protocol):
    """The vendor face of a timeline producer: one request, one envelope parse, nothing algebraic.

    **Speaks value types only** — never a `Domain`, `Selection`, `Coverage`, `Provenance`, or `Clock`.
    Each absence removes a way to be wrong rather than warning against it: a Probe with no clock cannot
    mis-stamp provenance, and one that never narrows a domain cannot mistake an unservable request for a
    vendor fault. Malformed or unparseable envelopes are its `RuntimeFailure`s to raise; whether a
    request is servable is settled before it is called.
    """

    reports_units: bool
    """Whether the vendor publishes unit tokens — a declaration the wrapper verifies, not trusts."""

    async def retrieve(
        self,
        *,
        longitude: float,
        latitude: float,
        over: Interval[datetime],
        variables: Sequence[str],
    ) -> TimelineDelivery: ...


@dataclass(frozen=True)
class TimelineDelivery:
    """One vendor response, parsed and no further — a Probe's entire account of a fetch.

    Vendor-keyed and pre-decode, because the vendor↔parameter map is many-to-many: a speed plus a
    direction jointly produce *both* wind components, so no `ParameterId` key is truthful yet. Units
    are the vendor's own; `reported_units` carries its claim about them when it publishes one.
    """

    valid_time: Sequence[datetime]
    series: Mapping[str, Sequence[float | None]]
    reported_units: Mapping[str, str] | None = None


@dataclass(frozen=True)
class TapTable:
    """What a timeline producer serves, and how each parameter is read out of vendor series.

    Declarations plus their execution. Everything here is value-level: which variables to ask for,
    what units they must arrive in, and what the numbers mean — anything needing a `Domain` is the
    wrapper's.
    """

    taps: tuple[PointSeriesTap, ...]

    def engaged_by(self, parameters: Collection[ParameterId]) -> TapTable:
        """The taps a request touches — a narrower table, which the whole fetch is then shaped from."""
        return TapTable(tuple(tap for tap in self.taps if tap.produces in parameters))

    @property
    def parameters(self) -> frozenset[ParameterId]:
        return frozenset(tap.produces for tap in self.taps)

    @property
    def variables(self) -> tuple[str, ...]:
        """The vendor variables to ask for, once each — two taps sharing a pair fetch it one time."""
        return tuple(dict.fromkeys(var.name for tap in self.taps for var in tap.vendor_vars))

    def by_level(self) -> Mapping[AxisSpec, tuple[PointSeriesTap, ...]]:
        """Taps grouped by the Z cell they sit at — one native record per group (ADR-0006)."""
        groups: dict[AxisSpec, list[PointSeriesTap]] = defaultdict(list)
        for tap in self.taps:
            groups[tap.z].append(tap)
        return {spec: tuple(group) for spec, group in groups.items()}

    def interpret(
        self, delivery: TimelineDelivery, *, source: str
    ) -> dict[ParameterId, ParameterData]:
        """Vendor series → canonical values, one slice per parameter: verify, convert, then decode.

        `source` names the producer in fault messages — the only thing here that knows a vendor exists.
        """
        converted = self._converted(delivery, source=source)
        ticks = len(delivery.valid_time)
        values: dict[ParameterId, ParameterData] = {}
        for tap in self.taps:
            data = tap.decode({var.name: converted[var.name] for var in tap.vendor_vars})
            if len(data.values) != ticks:
                raise RuntimeFailure(
                    f"{source} decode length mismatch for {tap.produces}: "
                    f"{len(data.values)} != {ticks}"
                )
            values[tap.produces] = data
        return values

    def _converted(
        self, delivery: TimelineDelivery, *, source: str
    ) -> dict[str, Sequence[float | None]]:
        """Each declared variable in canonical units — a report contradicting the declaration faults.

        **TODO (temporary):** the one conversion edge v1 has is wind km/h→m/s, hardcoded against the
        declared unit token; a verified conversion catalogue replaces both the check and the branch
        (docs/concerns.md#10-parameter-conventions).
        """
        reported = delivery.reported_units
        out: dict[str, Sequence[float | None]] = {}
        for var in {v.name: v for tap in self.taps for v in tap.vendor_vars}.values():
            if reported is not None:
                token = reported.get(var.name)
                if token is None or not _units_match(token, var.unit):
                    raise RuntimeFailure(
                        f"{source} unit mismatch for {var.name}: "
                        f"expected {var.unit!r}, got {token!r}"
                    )
            series = delivery.series.get(var.name)
            if series is None or len(series) != len(delivery.valid_time):
                raise RuntimeFailure(f"{source} series for {var.name} is malformed")
            out[var.name] = (
                [None if v is None else kmh_to_ms(v) for v in series]
                if var.unit == "km/h"
                else series
            )
        return out

    def __iter__(self) -> Iterator[PointSeriesTap]:
        return iter(self.taps)

    def __len__(self) -> int:
        return len(self.taps)


def _units_match(reported: str, expected: str) -> bool:
    """Whether a vendor's unit token means what the tap declared — spelling, not conversion."""
    if reported == expected:
        return True
    aliases = {
        "°C": {"°C", "degC", "celsius"},
        "degC": {"°C", "degC", "celsius"},
        "%": {"%", "percent"},
        "°": {"°", "degree", "degrees"},
        "km/h": {"km/h", "kmh"},
        "mm": {"mm"},
    }
    return reported in aliases.get(expected, {expected})


# --- What a producer declares ---


@dataclass(frozen=True)
class PointSeriesTap:
    """Tap for a point+timeline provider shape: one output parameter, one Z cell.

    X/Y (request-derived points) and T (provider rolling / hourly series) are structural to the
    shape — only `z` varies per parameter.
    """

    produces: ParameterId
    vendor_vars: tuple[VendorVar, ...]
    z: AxisSpec
    decode: Decode


@dataclass(frozen=True)
class VendorVar:
    """One vendor hourly field: its name and the unit token expected in the vendor's unit map."""

    name: str
    unit: str


class AxisMode(Enum):
    """How an `AxisSpec` materialises into an axis cell."""

    POINT = "point"
    SPAN = "span"


@dataclass(frozen=True)
class AxisSpec:
    """Geometric cell declaration: an interval plus whether it is a point sample or a span cell."""

    interval: Interval
    mode: AxisMode


Decode = Callable[[Mapping[str, Sequence[float | None]]], ParameterData]
"""Quantity transform over already unit-converted vendor series → one parameter's slice."""


def axis(spec: AxisSpec, *, name: AxisName = AxisName.Z) -> RegularAxis | IntervalAxis:
    """Materialise an `AxisSpec` into a footprint / native-record axis (POINT or SPAN)."""
    if spec.mode is AxisMode.POINT:
        level = spec.interval.lower
        if not isinstance(level, float):
            raise ValueError(f"POINT AxisSpec requires float interval, got {spec.interval!r}")
        return RegularAxis(name, level, 1.0, 1, cellular=False)
    return IntervalAxis(name, spec.interval)


def pointwise(*vars: str, fn: Callable[..., float]) -> Decode:
    """A tick is present iff every input var is; `fn` sees only present ticks.

    The value at an absent tick is unspecified filler (`nan`) — the mask is the sole
    presence authority. This is the only site that *writes* filler; downstream kernels
    then compute over it (`hypot(nan, nan)`), which the mask discards.
    """

    def decode(arrays: Mapping[str, Sequence[float | None]]) -> ParameterData:
        series = [arrays[v] for v in vars]
        values: list[float] = []
        present: list[bool] = []
        for cells in zip(*series, strict=True):
            if any(c is None for c in cells):
                values.append(float("nan"))
                present.append(False)
            else:
                values.append(fn(*cells))
                present.append(True)
        return ParameterData.of(values, present)

    return decode


def passthrough(var: str) -> Decode:
    """Decode that copies one already-converted vendor series into canonical values."""
    return pointwise(var, fn=lambda v: v)


# --- Shared hourly / vertical presets (tap building blocks) ---

HOURLY_STEP = timedelta(hours=1)

# Conventional tropopause-scale upper for a total-cloud column cell (stand-in; vendors rarely publish TOA).
TOA_M = 15_000.0

Z_1_5M = AxisSpec(Interval(1.5, 1.5), AxisMode.POINT)
Z_2M = AxisSpec(Interval(2.0, 2.0), AxisMode.POINT)
Z_10M = AxisSpec(Interval(10.0, 10.0), AxisMode.POINT)
Z_SURFACE = AxisSpec(Interval(0.0, 0.0), AxisMode.POINT)
Z_COLUMN = AxisSpec(Interval(0.0, TOA_M), AxisMode.SPAN)
