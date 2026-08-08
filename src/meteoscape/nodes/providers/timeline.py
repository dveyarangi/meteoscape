"""Point+timeline provider shape — the `Provider` a whole family of vendors is served by.

A timeline producer delivers a single X/Y point and a regular T series; only Z varies per parameter.
`TimelineProvider` implements that shape and owns every algebraic step, while the vendor arrives as an
injected `TimelineProbe` that builds one request and parses one envelope. Other provider shapes
(gridded NWP, soundings) are a deferred seam — they add a wrapper beside this one, never a Probe.

The contract both halves answer to is [edge/provider.md](../../../../docs/edge/provider.md).
"""

from __future__ import annotations

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
from ...manifold.core import Coverage, Manifold, Selection
from ...manifold.coverage import CoverageRecord
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
)
from ...manifold.provenance import AtomicOrigin, Provenance, Uniform
from ...manifold.sampling import Shortfall, resample
from ...parameters import ParameterDef, ParameterId
from ..catalog.paramtable import ParameterTable
from .base import Provider
from .normalization import kmh_to_ms

GLOBAL_LONGITUDES = Interval(-180.0, 180.0)
GLOBAL_LATITUDES = Interval(-90.0, 90.0)
"""The whole-globe reach a worldwide point API declares by saying nothing; a regional one overrides."""


class TimelineProvider(Provider):
    """A point plus a series, from whichever vendor delivers one — the shape, not the endpoint.

    Owns every algebraic step, so a producer of this shape contributes declarations and a
    `TimelineProbe` and no algebra of its own — the property that keeps snap arithmetic out of every
    vendor leaf after the first. Its constructor arguments are **per-offering** facts, carrying one
    offering's worth in v1
    ([#20](../../../../docs/concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)).
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
        self._probe = probe
        self._taps = taps
        self._step = step
        self._cadence = cadence
        self._clock = clock
        self._parameters = parameters
        self._source_key = source_key
        self._source = source_key.provider
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

    async def project(self, selection: Selection) -> Manifold:
        engaged = self._taps.engaged_by(selection.parameters)
        if not engaged:
            raise RuntimeFailure(f"{self._source} Selection requests no served parameters")
        wanted = self._resolve(selection.domain, engaged)
        longitude, latitude = self._point_of(wanted)
        delivery = await self._probe.retrieve(
            longitude=longitude,
            latitude=latitude,
            over=self._window_of(wanted),
            variables=engaged.variables,
        )
        records = self._interpret(delivery, engaged, longitude=longitude, latitude=latitude)
        return self._assemble(records, selection)

    @property
    def capability(self) -> GranularCapability:
        return self._capability

    @property
    def source_key(self) -> SourceKey:
        return self._source_key

    # --- Resolution: what the declarations answer with, before anything is fetched ---

    def _resolve(self, request: Domain, taps: TapTable) -> GridDomain:
        """The pre-fetch `ground`: what this producer's own declared geometry answers the request with.

        One fetch carries one geometry, so the engaged taps must ground alike — their footprints
        differ only in Z, which a request pins itself.
        """
        try:
            wanted = agreed_geometry(
                ground(request, self._footprints[tap.produces][1]) for tap in taps
            )
        except ValueError as exc:
            raise CapabilityMismatch(f"{self._source} cannot serve this selection: {exc}") from exc
        # `ground` builds a grid; v1 mints no other enumerable representation.
        assert isinstance(wanted, GridDomain)
        return wanted

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
    ) -> Sequence[Coverage]:
        """The vendor's account as native records: canonical values on the geometry delivered.

        One record per Z cell (ADR-0006) — every parameter's values are positional to the delivered
        ticks alone, so what groups them is the only axis that varies. X/Y are the point asked at: a
        vendor echoing its own snapped cell centre is answering a question resolution already settled.
        """
        if self._probe.reports_units and delivery.reported_units is None:
            raise RuntimeFailure(f"{self._source} declares reported units but delivered none")
        values = taps.interpret(delivery, source=self._source)
        valid_time = self._lattice_of(delivery.valid_time)
        provenance = Uniform(self._stamp())
        records: list[Coverage] = []
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

    def _stamp(self) -> Provenance:
        """One fetch, one plane: the run this answer came from, and when it goes stale (ADR-0003)."""
        now = self._clock.now()
        return Provenance(
            origin=AtomicOrigin(self._source_key, self._cadence.anchor(now)),
            fetched_at=now,
            expiration=self._cadence.expiration(now),
        )

    # --- Assembly: the answer, on the geometry the request asked for ---

    def _assemble(self, records: Sequence[Coverage], selection: Selection) -> CoverageRecord:
        """One Coverage from one fetch: resolve the request against what arrived, then crop to it.

        Both request modes take this path — grounding an already-exact request is the identity, so
        what would be a mode branch is an equality that happens to hold. The vendor is the authority
        on what exists and the request on what is in bounds, which is why a wider answer is trimmed
        rather than refused; only a series missing the bounds entirely leaves nothing to answer with.
        """
        if not records:
            raise RuntimeFailure(f"{self._source} assemble received no native records")
        answer = self._answered_geometry(records, selection)
        return self._cropped(
            self._as_delivered(records, selection, answer), answer, selection.parameters
        )

    def _answered_geometry(self, records: Sequence[Coverage], selection: Selection) -> GridDomain:
        """The geometry this fetch answers with: the request, resolved against every record delivered.

        The fold is a **law, not a live guard here** — do not read it as one: this shape stamps one
        derived lattice onto every record and Z grounds by identity, so its records cannot disagree. It
        is kept because a shape deriving a lattice *per record* would need it, and because divergence
        between the two fetches of one request is the **Arbiter's** to catch, never this.
        """
        try:
            answer = agreed_geometry(ground(selection.domain, record.domain) for record in records)
        except ValueError as exc:
            raise CapabilityMismatch(f"{self._source} cannot answer this selection: {exc}") from exc
        # The answer of a grounded request is a grid; the crop reads it per axis.
        assert isinstance(answer, GridDomain)
        return answer

    def _as_delivered(
        self, records: Sequence[Coverage], selection: Selection, answer: GridDomain
    ) -> CoverageRecord:
        """The fetch as parsed: the answer's geometry carried on the vendor's own tick lattice.

        Every record is one response's series at one Z, and X/Y/Z are single cells, so each
        parameter's values are positional to the delivered ticks — which is what lets one Coverage
        hold them all.
        """
        ranges: dict[ParameterId, ParameterData] = {}
        parameters: dict[ParameterId, ParameterDef] = {}
        for record in records:
            for pid, data in record.ranges.items():
                if pid in selection.parameters:
                    ranges[pid] = data
                    parameters[pid] = record.capability.parameters[pid]

        missing = selection.parameters - ranges.keys()
        if missing:
            raise RuntimeFailure(f"{self._source} assemble missing parameter(s): {sorted(missing)}")

        # One response, one lattice: every record's T is built from the same delivered series.
        delivered = records[0].domain
        assert isinstance(delivered, GridDomain)
        return CoverageRecord(
            capability=EnumerableCapability(
                domain=GridDomain(axes={**answer.axes, AxisName.T: delivered.axis(AxisName.T)}),
                parameters=parameters,
            ),
            ranges=ranges,
            provenance=records[0].provenance,
        )

    def _cropped(
        self, delivered: CoverageRecord, answer: GridDomain, parameters: frozenset[ParameterId]
    ) -> CoverageRecord:
        """Trim the delivered series to the answer — a no-op when the vendor gave exactly it.

        A `Shortfall` can only come from an **exact** request: a snapped answer is grounded against the
        delivery, so there is nothing for it to fall short of. It means the caller's own coordinates went
        unanswered — aligned, short by a known count, and a fault rather than an unservable request.
        Interim: when concern #30 pads that tail, both this branch and the failure go.
        """
        if delivered.domain == answer:
            return delivered
        try:
            return resample(delivered, Selection(domain=answer, parameters=parameters))
        except Shortfall as exc:
            raise RuntimeFailure(f"{self._source} delivered less than it declared: {exc}") from exc


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
    ([#12](../../../../docs/concerns.md), source role). The wrapper keeps the narrow map because it
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

        **Interim:** the one conversion edge v1 has is wind km/h→m/s, hardcoded against the declared
        unit token; a verified conversion catalogue would replace both the check and the conversion.
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

Z_2M = AxisSpec(Interval(2.0, 2.0), AxisMode.POINT)
Z_10M = AxisSpec(Interval(10.0, 10.0), AxisMode.POINT)
Z_SURFACE = AxisSpec(Interval(0.0, 0.0), AxisMode.POINT)
Z_COLUMN = AxisSpec(Interval(0.0, TOA_M), AxisMode.SPAN)
