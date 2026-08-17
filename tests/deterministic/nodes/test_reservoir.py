"""`Reservoir` retention pipeline — read-back, serve-vs-refetch gate, and project."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fakes import STOPPED, core_parameters, footprint_capability, footprint_domain
from meteoscape.clock import Clock
from meteoscape.errors import CapabilityMismatch, RuntimeFailure
from meteoscape.identity import SourceKey
from meteoscape.manifold.cadence import CadenceDef
from meteoscape.manifold.capability import EnumerableCapability, GranularCapability
from meteoscape.manifold.core import Manifold, Selection
from meteoscape.manifold.coverage import CoverageRecord, CoverageSet
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import (
    AxisName,
    ContinuousAxis,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
    SelectionDomain,
    SnappedAxis,
    VantageAxis,
    agreed_geometry,
    ground,
)
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.reservoir import Reservoir
from meteoscape.nodes.store import MemoryStore
from meteoscape.parameters import AIR_TEMPERATURE, PRECIPITATION, WIND_U, ParameterId

_START = datetime(2026, 7, 11, tzinfo=UTC)
_FETCHED = datetime(2026, 7, 11, 12, tzinfo=UTC)
_GAP_NOW = datetime(2026, 7, 11, 11, 42, tzinfo=UTC)
_FIRST_TICK = datetime(2026, 7, 11, 12, tzinfo=UTC)
_HOUR = timedelta(hours=1)
# Shelf finer than cadence: reach advances before expiry — the defect-2 shape (TWC-like).
_LATE_CADENCE = CadenceDef(
    cadence=12 * _HOUR,
    publication_latency=timedelta(0),
    max_lead=24 * _HOUR,
    shelf=_HOUR,
)


class _AdvancingClock:
    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant


def _native(*, lon: float, lat: float, z: float = 2.0, hours: int = 4) -> GridDomain:
    return GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, lon, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, lat, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, z, 1.0, 1, False),
            AxisName.T: RegularAxis(AxisName.T, _FETCHED, timedelta(hours=1), hours, False),
        }
    )


def _record(
    pid: ParameterId,
    domain: GridDomain,
    *,
    value: float = 1.0,
    fetched_at: datetime = _FETCHED,
    expiration: datetime | None = None,
) -> CoverageRecord:
    return CoverageRecord(
        capability=EnumerableCapability(
            domain=domain, parameters={pid: core_parameters().get(pid)}
        ),
        ranges={pid: ParameterData(values=[value] * len(domain), present=None)},
        provenance=Uniform(
            Provenance(
                origin=AtomicOrigin(SourceKey("fake", "default"), fetched_at),
                fetched_at=fetched_at,
                expiration=expiration or (fetched_at + timedelta(hours=1)),
            )
        ),
    )


def _ask(
    *,
    lon: float,
    lat: float,
    start: datetime,
    end: datetime,
    z: Interval[float] | None = None,
) -> SelectionDomain:
    """Edge-shaped ask: pinned X/Y, vantage Z, snapped T — the relabel target."""
    return SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, lon, 0.0001, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, lat, 0.0001, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, z or Interval(0.0, 10.0)),
            AxisName.T: SnappedAxis(AxisName.T, Interval(start, end)),
        }
    )


def _timeline_store(*, clock: Clock = STOPPED) -> MemoryStore:
    return MemoryStore(
        grids={
            AxisName.X: RegularAxis(AxisName.X, -180.0, 0.5, 721, cellular=True),
            AxisName.Y: RegularAxis(AxisName.Y, -90.0, 0.5, 361, cellular=True),
        },
        deferred=frozenset({AxisName.T, AxisName.Z}),
        clock=clock,
        retention=timedelta(days=14),
    )


def _reservoir() -> Reservoir:
    """Any store + child — stage-1 helpers never touch `project`."""
    store = _timeline_store()

    class _Silent(Manifold):
        async def project(self, selection: Selection) -> Manifold:
            raise AssertionError("read-back tests must not call the child")

        @property
        def capability(self):  # type: ignore[no-untyped-def]
            raise AssertionError("read-back tests must not read capability")

    return Reservoir(store, _Silent(), STOPPED)


class _Counting(Manifold):
    """Child that records calls and returns a fixed multi-domain answer."""

    def __init__(
        self,
        records: tuple[CoverageRecord, ...],
        pids: frozenset[ParameterId],
        *,
        z: Interval[float] | None = None,
    ) -> None:
        self.calls = 0
        self.asked: list[frozenset[ParameterId]] = []
        self._answer = CoverageSet(records)
        table = core_parameters()
        if z is None:
            self._capability = footprint_capability(STOPPED, table, pids)
        else:
            # A declared Z that genuinely covers the native cell, so vantage asks admit the way the
            # Arbiter would in production — `fakes`' default Z is the degenerate [0, 0].
            declared = FootprintDomain(
                axes={**footprint_domain(STOPPED).axes, AxisName.Z: ContinuousAxis(AxisName.Z, z)}
            )
            self._capability = GranularCapability(
                reaches={pid: (table.get(pid), declared) for pid in pids}
            )

    async def project(self, selection: Selection) -> Manifold:
        self.calls += 1
        self.asked.append(selection.parameters)
        return self._answer

    @property
    def capability(self):  # type: ignore[no-untyped-def]
        return self._capability


class _Widening(_Counting):
    """Child that answers a wider timeline on the refetch — the extension case's second run."""

    def __init__(
        self,
        first: tuple[CoverageRecord, ...],
        then: tuple[CoverageRecord, ...],
        pids: frozenset[ParameterId],
    ) -> None:
        super().__init__(first, pids)
        self._then = CoverageSet(then)

    async def project(self, selection: Selection) -> Manifold:
        answer = await super().project(selection)
        return answer if self.calls == 1 else self._then


class _Echoing(_Counting):
    """Child that answers on the asked X/Y — what a real Provider does (open_meteo.py:164).

    Its inherited `_answer` is never returned; the placeholder record it is built with only keeps
    `_Counting.__init__` honest.
    """

    async def project(self, selection: Selection) -> Manifold:
        self.calls += 1
        self.asked.append(selection.parameters)
        # `quantize` hands the store's fetch-order, always a SelectionDomain (store.py:185-208).
        assert isinstance(selection.domain, SelectionDomain)
        lon = selection.domain.axis(AxisName.X).extent.lower
        lat = selection.domain.axis(AxisName.Y).extent.lower
        assert isinstance(lon, float) and isinstance(lat, float)
        return CoverageSet((_record(AIR_TEMPERATURE, _native(lon=lon, lat=lat), value=7.5),))


def _live_ask(
    *,
    lon: float = 10.0,
    lat: float = 20.0,
    hours: int = 3,
    z: Interval[float] | None = None,
) -> Selection:
    return Selection(
        _ask(
            lon=lon,
            lat=lat,
            start=_FETCHED,
            end=_FETCHED + timedelta(hours=hours),
            z=z,
        ),
        frozenset({AIR_TEMPERATURE}),
    )


def _late_native(*, hours: int = 9) -> GridDomain:
    """Vendor series starting at the next whole hour — after the declared window opens."""
    return GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 10.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 20.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
            AxisName.T: RegularAxis(AxisName.T, _FIRST_TICK, _HOUR, hours, False),
        }
    )


class _LateSeries(Manifold):
    """Rolling leaf whose delivered T starts after the declared window — TWC's default shape."""

    def __init__(
        self,
        clock: Clock,
        records: tuple[CoverageRecord, ...],
        pids: frozenset[ParameterId],
        *,
        cadence: CadenceDef = _LATE_CADENCE,
    ) -> None:
        self.calls = 0
        self._answer = CoverageSet(records)
        self._capability = footprint_capability(clock, core_parameters(), pids, cadence=cadence)

    async def project(self, selection: Selection) -> Manifold:
        self.calls += 1
        return self._answer

    @property
    def capability(self):  # type: ignore[no-untyped-def]
        return self._capability


def _gap_ask(*, start: datetime = _GAP_NOW, end: datetime | None = None) -> Selection:
    return Selection(
        _ask(lon=10.0, lat=20.0, start=start, end=end or (start + 3 * _HOUR)),
        frozenset({AIR_TEMPERATURE}),
    )


# --- Read-back ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_relabel_leaves_values_and_provenance_identical() -> None:
    """The claim changes address only — values and provenance are untouched."""
    native = _native(lon=10.0, lat=20.0)
    held = CoverageSet((_record(AIR_TEMPERATURE, native, value=7.5),))
    ask = _ask(lon=10.05, lat=20.05, start=_FETCHED, end=_FETCHED + timedelta(hours=1))
    served = await _reservoir()._read_back(held, Selection(ask, frozenset({AIR_TEMPERATURE})))
    assert isinstance(served, CoverageRecord)
    assert served.ranges[AIR_TEMPERATURE].values == pytest.approx([7.5, 7.5])
    assert served.provenance == held.records[0].provenance


@pytest.mark.asyncio
async def test_raw_carrier_raises_where_relabelled_folds() -> None:
    """Relabel is load-bearing: the raw multi-domain carrier cannot fold onto a vantage ask."""
    temp = _record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0, z=2.0))
    wind = _record(WIND_U, _native(lon=10.0, lat=20.0, z=10.0))
    ask = _ask(lon=10.0, lat=20.0, start=_FETCHED, end=_FETCHED + timedelta(hours=1))
    selection = Selection(ask, frozenset({AIR_TEMPERATURE, WIND_U}))
    carrier = CoverageSet((temp, wind))
    # Against the *grounded* target, so the only difference between the arms is the relabel: the
    # sampler refuses to cross native Z onto the asked vantage and names this node as the owner.
    # Folding the raw carrier onto the SelectionDomain ask would raise too,
    # but for an unrelated reason — a carrier folds onto enumerable geometry only.
    target = agreed_geometry(
        (ground(ask, record.domain) for record in carrier.records), request=ask
    )
    with pytest.raises(NotImplementedError, match="requires Reservoir homogenization"):
        await carrier.project(Selection(target, selection.parameters))
    served = await _reservoir()._read_back(carrier, selection)
    assert isinstance(served, CoverageRecord)
    assert AIR_TEMPERATURE in served.ranges and WIND_U in served.ranges


@pytest.mark.asyncio
async def test_bounded_t_crops_and_any_passes_whole() -> None:
    """Bounded T crops at the fold; `ANY` keeps the held timeline whole."""
    native = _native(lon=10.0, lat=20.0, hours=4)
    held = CoverageSet((_record(AIR_TEMPERATURE, native),))
    bounded = await _reservoir()._read_back(
        held,
        Selection(
            _ask(lon=10.0, lat=20.0, start=_FETCHED, end=_FETCHED + timedelta(hours=1)),
            frozenset({AIR_TEMPERATURE}),
        ),
    )
    assert isinstance(bounded, CoverageRecord)
    assert len(bounded.domain) == 2  # inclusive end → two ticks
    open_ask = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 10.0, 0.0001, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 20.0, 0.0001, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: SnappedAxis(AxisName.T, None),
        }
    )
    whole = await _reservoir()._read_back(held, Selection(open_ask, frozenset({AIR_TEMPERATURE})))
    assert isinstance(whole, CoverageRecord)
    assert len(whole.domain) == 4


@pytest.mark.asyncio
async def test_multi_parameter_merge_keeps_one_issue_time() -> None:
    """Two native heights fold onto one vantage answer with one shared issue_time."""
    temp = _record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0, z=2.0))
    wind = _record(WIND_U, _native(lon=10.0, lat=20.0, z=10.0))
    ask = _ask(lon=10.0, lat=20.0, start=_FETCHED, end=_FETCHED + timedelta(hours=1))
    served = await _reservoir()._read_back(
        CoverageSet((temp, wind)), Selection(ask, frozenset({AIR_TEMPERATURE, WIND_U}))
    )
    assert isinstance(served, CoverageRecord)
    for pid in (AIR_TEMPERATURE, WIND_U):
        origin = served.provenance.summary(pid).origin
        assert isinstance(origin, AtomicOrigin)
        assert origin.issue_time == _FETCHED


@pytest.mark.asyncio
async def test_target_fold_value_error_is_runtime_failure() -> None:
    """Holdings that ground to different lattices are an engine invariant break, not a bad ask.

    Two Holdings on **different T steps** ground to two geometries the request bounds, so
    `agreed_geometry` refuses — and the refusal must arrive as `RuntimeFailure`: admission and the
    store already decided these Holdings answer this ask. Deliberately
    *non-empty*: an empty carrier short-circuits earlier, on a different sentence.
    """
    hourly = _record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0, hours=4))
    two_hourly = _record(
        PRECIPITATION,
        GridDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, 10.0, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, 20.0, 1.0, 1, False),
                AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
                AxisName.T: RegularAxis(AxisName.T, _FETCHED, timedelta(hours=2), 2, False),
            }
        ),
    )
    ask = _ask(lon=10.0, lat=20.0, start=_FETCHED, end=_FETCHED + timedelta(hours=1))
    with pytest.raises(RuntimeFailure, match="cannot ground onto an admitted request"):
        await _reservoir()._read_back(
            CoverageSet((hourly, two_hourly)),
            Selection(ask, frozenset({AIR_TEMPERATURE, PRECIPITATION})),
        )


# --- Pipeline / source-group -------------------------------------------------


@pytest.mark.asyncio
async def test_project_refills_then_serves_from_store() -> None:
    """Cold ask refills via the child; a fresh repeat does not call the child again."""
    child = _Counting(
        (_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0)),), frozenset({AIR_TEMPERATURE})
    )
    reservoir = Reservoir(_timeline_store(), child, STOPPED)
    first = await reservoir.project(_live_ask())
    second = await reservoir.project(_live_ask())
    assert child.calls == 1
    assert isinstance(first, CoverageRecord)
    assert isinstance(second, CoverageRecord)


@pytest.mark.asyncio
async def test_off_grid_request_is_answered_at_the_requested_point() -> None:
    """Off-grid X/Y are reported at the ask; values come from the enclosing store cell."""
    child = _Counting(
        (_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0), value=7.5),),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(), child, STOPPED)
    served = await reservoir.project(_live_ask(lon=10.3, lat=20.2))
    assert isinstance(served, CoverageRecord)
    assert isinstance(served.domain, GridDomain)
    assert served.domain.axis(AxisName.X)[0].coordinate == 10.3
    assert served.domain.axis(AxisName.Y)[0].coordinate == 20.2
    assert served.ranges[AIR_TEMPERATURE].values == pytest.approx([7.5] * len(served.domain))


@pytest.mark.asyncio
async def test_two_points_in_one_store_cell_share_one_fetch() -> None:
    """Two asks inside one store cell share one refill; each answer keeps its own label."""
    child = _Counting(
        (_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0), value=7.5),),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(), child, STOPPED)
    first = await reservoir.project(_live_ask(lon=10.3))
    second = await reservoir.project(_live_ask(lon=10.4))
    assert child.calls == 1
    assert isinstance(first, CoverageRecord) and isinstance(second, CoverageRecord)
    assert isinstance(first.domain, GridDomain) and isinstance(second.domain, GridDomain)
    assert first.domain.axis(AxisName.X)[0].coordinate == 10.3
    assert second.domain.axis(AxisName.X)[0].coordinate == 10.4
    assert first.ranges[AIR_TEMPERATURE].values == second.ranges[AIR_TEMPERATURE].values


@pytest.mark.asyncio
async def test_points_in_different_store_cells_fetch_separately() -> None:
    """Asks in different store cells each refill — enclosing is per cell, not nearest-global."""
    child = _Echoing(
        (_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0)),),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(), child, STOPPED)
    first = await reservoir.project(_live_ask(lon=10.3))
    second = await reservoir.project(_live_ask(lon=10.6))
    assert child.calls == 2
    assert isinstance(first, CoverageRecord) and isinstance(second, CoverageRecord)
    assert isinstance(first.domain, GridDomain) and isinstance(second.domain, GridDomain)
    assert first.domain.axis(AxisName.X)[0].coordinate == 10.3
    assert second.domain.axis(AxisName.X)[0].coordinate == 10.6


@pytest.mark.asyncio
async def test_on_grid_request_is_the_identity_crop() -> None:
    """An on-tick ask is a lossless crop: the coordinate is unchanged and values are untouched.

    Relabel still runs. It harmonizes the whole axis object, and the held record carries the
    provider's native `step` (1.0) where the ask carries the edge's (0.0001) - skipping it here
    raises `NotImplementedError` from `resample`, on-grid as much as off. What is identity in this
    case is the coordinate and the values, not the rewrite.
    """
    child = _Counting(
        (_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0), value=7.5),),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(), child, STOPPED)
    served = await reservoir.project(_live_ask())
    assert isinstance(served, CoverageRecord)
    assert isinstance(served.domain, GridDomain)
    assert served.domain.axis(AxisName.X)[0].coordinate == 10.0
    assert served.domain.axis(AxisName.Y)[0].coordinate == 20.0
    assert served.ranges[AIR_TEMPERATURE].values == pytest.approx([7.5] * len(served.domain))


@pytest.mark.asyncio
async def test_expired_holding_triggers_refill() -> None:
    """Per-Holding freshness: an expired Holding refills; the Arbiter path never serves stale."""
    clock = _AdvancingClock(_FETCHED)
    child = _Counting(
        (_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0)),), frozenset({AIR_TEMPERATURE})
    )
    reservoir = Reservoir(_timeline_store(clock=clock), child, clock)
    await reservoir.project(_live_ask())
    assert child.calls == 1
    clock.instant = _FETCHED + timedelta(hours=2)  # past expiration (= fetched+1h)
    await reservoir.project(_live_ask())
    assert child.calls == 2


@pytest.mark.asyncio
async def test_differing_expirations_refill_only_the_stale_parameter() -> None:
    """Freshness is per Holding, not per request: the fresh one serves beside the stale one.

    A single-cadence Source's Holdings age together, so the test separates their expirations to pin
    the per-Holding gate.
    """
    clock = _AdvancingClock(_FETCHED)
    long_lived = _record(
        AIR_TEMPERATURE, _native(lon=10.0, lat=20.0), expiration=_FETCHED + timedelta(hours=6)
    )
    short_lived = _record(
        PRECIPITATION, _native(lon=10.0, lat=20.0), expiration=_FETCHED + timedelta(hours=1)
    )
    child = _Counting((long_lived, short_lived), frozenset({AIR_TEMPERATURE, PRECIPITATION}))
    reservoir = Reservoir(_timeline_store(clock=clock), child, clock)
    ask = Selection(
        _ask(lon=10.0, lat=20.0, start=_FETCHED, end=_FETCHED + timedelta(hours=1)),
        frozenset({AIR_TEMPERATURE, PRECIPITATION}),
    )

    await reservoir.project(ask)
    assert child.calls == 1
    clock.instant = _FETCHED + timedelta(hours=2)  # precipitation expired; temperature has not

    served = await reservoir.project(ask)

    assert child.calls == 2
    assert isinstance(served, CoverageRecord)
    assert {AIR_TEMPERATURE, PRECIPITATION} <= served.ranges.keys()
    # The refill named only the stale parameter — the fresh one was never re-asked for.
    assert child.asked[-1] == frozenset({PRECIPITATION})


@pytest.mark.asyncio
async def test_z_reuse_across_compatible_vantages() -> None:
    """A later ask whose Z still admits the native cell reuses the retained Holding — no refetch.

    The child declares its native 2 m cell, so **both** vantages below admit it at the Arbiter the
    way production would: the reuse being proven is the store's, not an artifact of a fake whose
    declared Z no request could match.
    """
    child = _Counting(
        (_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0, z=2.0)),),
        frozenset({AIR_TEMPERATURE}),
        z=Interval(2.0, 2.0),
    )
    reservoir = Reservoir(_timeline_store(), child, STOPPED)
    await reservoir.project(_live_ask(z=Interval(0.0, 10.0)))
    await reservoir.project(_live_ask(z=Interval(1.0, 5.0)))
    assert child.calls == 1


@pytest.mark.asyncio
async def test_holding_fallen_behind_now_refetches_the_whole_holding() -> None:
    """A rolling Holding that no longer reaches the ask triggers a whole-Holding refill.

    A clock-anchored window cannot grow with the clock stopped; the real refetch case is the
    horizon falling behind `now` (ADR-0002).
    """
    clock = _AdvancingClock(_FIRST_TICK)
    behind = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 10.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 20.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
            AxisName.T: RegularAxis(AxisName.T, _FIRST_TICK - 5 * _HOUR, _HOUR, 3, False),
        }
    )
    current = _late_native(hours=9)
    child = _LateSeries(
        clock,
        (
            _record(
                AIR_TEMPERATURE,
                current,
                value=2.0,
                fetched_at=_FIRST_TICK,
                expiration=_FIRST_TICK + 12 * _HOUR,
            ),
        ),
        frozenset({AIR_TEMPERATURE}),
    )
    store = _timeline_store(clock=clock)
    await store.assimilate(
        CoverageSet(
            (
                _record(
                    AIR_TEMPERATURE,
                    behind,
                    value=1.0,
                    fetched_at=_FIRST_TICK - 5 * _HOUR,
                    expiration=_FIRST_TICK + 12 * _HOUR,
                ),
            )
        )
    )
    reservoir = Reservoir(store, child, clock)
    served = await reservoir.project(_gap_ask(start=_FIRST_TICK, end=_FIRST_TICK + 3 * _HOUR))
    assert child.calls == 1
    assert isinstance(served, CoverageRecord)
    assert served.ranges[AIR_TEMPERATURE].values == pytest.approx([2.0] * len(served.domain))


@pytest.mark.asyncio
async def test_static_t_still_refetches_on_a_wider_ask() -> None:
    """Case E at the Reservoir: a static T corpus is a slice — a wider ask needs more data."""
    short = _native(lon=10.0, lat=20.0, hours=2)
    full = _native(lon=10.0, lat=20.0, hours=4)
    table = core_parameters()
    static_reach = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(
                AxisName.T, Interval(_FETCHED, _FETCHED + timedelta(hours=24))
            ),
        }
    )

    class _StaticWidening(_Widening):
        @property
        def capability(self):  # type: ignore[no-untyped-def]
            return GranularCapability(
                reaches={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), static_reach)}
            )

    child = _StaticWidening(
        (_record(AIR_TEMPERATURE, short, value=1.0),),
        (_record(AIR_TEMPERATURE, full, value=2.0),),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(), child, STOPPED)
    await reservoir.project(_live_ask(hours=1))
    assert child.calls == 1
    served = await reservoir.project(_live_ask(hours=3))
    assert child.calls == 2
    assert isinstance(served, CoverageRecord)
    assert len(served.domain) == 4
    assert served.ranges[AIR_TEMPERATURE].values == pytest.approx([2.0] * 4)


@pytest.mark.asyncio
async def test_gap_ask_refills_at_most_once() -> None:
    """Defect 1: a default ask in the declared-but-undelivered gap warms after one child call."""
    clock = _AdvancingClock(_GAP_NOW)
    child = _LateSeries(
        clock,
        (
            _record(
                AIR_TEMPERATURE,
                _late_native(),
                fetched_at=_GAP_NOW,
                expiration=_GAP_NOW + 12 * _HOUR,
            ),
        ),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(clock=clock), child, clock)
    await reservoir.project(_gap_ask())
    await reservoir.project(_gap_ask())
    assert child.calls == 1


@pytest.mark.asyncio
async def test_shelf_advance_does_not_outrank_cadence() -> None:
    """Defect 2: crossing a Shelf boundary before expiry makes no vendor call."""
    clock = _AdvancingClock(_GAP_NOW)
    child = _LateSeries(
        clock,
        (
            _record(
                AIR_TEMPERATURE,
                _late_native(),
                fetched_at=_GAP_NOW,
                expiration=_GAP_NOW + 12 * _HOUR,
            ),
        ),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(clock=clock), child, clock)
    await reservoir.project(_gap_ask())
    assert child.calls == 1
    clock.instant = _GAP_NOW + _HOUR  # past Shelf, still before stamped expiry
    await reservoir.project(_gap_ask(start=clock.instant, end=clock.instant + 3 * _HOUR))
    assert child.calls == 1


@pytest.mark.asyncio
async def test_expiry_still_refetches_after_shelf_advance() -> None:
    """Freshness still governs: past stamped expiry, the gate refills."""
    clock = _AdvancingClock(_GAP_NOW)
    child = _LateSeries(
        clock,
        (
            _record(
                AIR_TEMPERATURE,
                _late_native(),
                fetched_at=_GAP_NOW,
                expiration=_GAP_NOW + 2 * _HOUR,
            ),
        ),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(clock=clock), child, clock)
    await reservoir.project(_gap_ask())
    assert child.calls == 1
    clock.instant = _GAP_NOW + 3 * _HOUR
    await reservoir.project(_gap_ask(start=clock.instant, end=clock.instant + 3 * _HOUR))
    assert child.calls == 2


@pytest.mark.asyncio
async def test_straddling_gap_serves_from_first_delivered_tick() -> None:
    """A request that crosses the gap serves the overlap; first tick is the vendor's first."""
    clock = _AdvancingClock(_GAP_NOW)
    child = _LateSeries(
        clock,
        (
            _record(
                AIR_TEMPERATURE,
                _late_native(hours=4),
                fetched_at=_GAP_NOW,
                expiration=_GAP_NOW + 12 * _HOUR,
            ),
        ),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(clock=clock), child, clock)
    served = await reservoir.project(_gap_ask(start=_GAP_NOW, end=_FIRST_TICK + 3 * _HOUR))
    assert isinstance(served, CoverageRecord)
    assert isinstance(served.domain, GridDomain)
    assert served.domain.axis(AxisName.T)[0].coordinate == _FIRST_TICK


@pytest.mark.asyncio
async def test_wholly_in_gap_ask_is_capability_mismatch_without_refetch_when_warm() -> None:
    """Warm in-gap ask: CapabilityMismatch, and no further child call (check is not in refill)."""
    clock = _AdvancingClock(_GAP_NOW)
    child = _LateSeries(
        clock,
        (
            _record(
                AIR_TEMPERATURE,
                _late_native(),
                fetched_at=_GAP_NOW,
                expiration=_GAP_NOW + 12 * _HOUR,
            ),
        ),
        frozenset({AIR_TEMPERATURE}),
    )
    reservoir = Reservoir(_timeline_store(clock=clock), child, clock)
    # Straddle first so the store is warm; an in-gap ask must not refill to look green.
    await reservoir.project(_gap_ask(start=_FIRST_TICK, end=_FIRST_TICK + 3 * _HOUR))
    assert child.calls == 1
    in_gap = _gap_ask(
        start=_GAP_NOW.replace(minute=10),
        end=_GAP_NOW.replace(minute=50),
    )
    with pytest.raises(CapabilityMismatch, match="holdings do not meet asked T"):
        await reservoir.project(in_gap)
    with pytest.raises(CapabilityMismatch, match="holdings do not meet asked T"):
        await reservoir.project(in_gap)
    assert child.calls == 1


@pytest.mark.asyncio
async def test_unserved_parameter_is_omitted() -> None:
    """Asked parameters the child does not serve are omitted — no raise on the partial set."""
    child = _Counting(
        (_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0)),), frozenset({AIR_TEMPERATURE})
    )
    reservoir = Reservoir(_timeline_store(), child, STOPPED)
    served = await reservoir.project(
        Selection(
            _ask(lon=10.0, lat=20.0, start=_FETCHED, end=_FETCHED + timedelta(hours=1)),
            frozenset({AIR_TEMPERATURE, PRECIPITATION}),
        )
    )
    assert isinstance(served, CoverageRecord)
    assert AIR_TEMPERATURE in served.ranges
    assert PRECIPITATION not in served.ranges
    assert child.calls == 1


@pytest.mark.asyncio
async def test_wholly_unservable_request_is_capability_mismatch() -> None:
    """Nothing the child serves → CapabilityMismatch, matching Arbiter empty-admission."""
    child = _Counting(
        (_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0)),), frozenset({AIR_TEMPERATURE})
    )
    reservoir = Reservoir(_timeline_store(), child, STOPPED)
    with pytest.raises(CapabilityMismatch):
        await reservoir.project(
            Selection(
                _ask(lon=10.0, lat=20.0, start=_FETCHED, end=_FETCHED + timedelta(hours=1)),
                frozenset({PRECIPITATION}),
            )
        )
    assert child.calls == 0


@pytest.mark.asyncio
async def test_parameter_whose_reach_left_the_window_is_not_served_from_holdings() -> None:
    """Admission gates serving, not just refilling: a held-but-unreachable parameter is omitted.

    Its reach no longer covers the request, so the gate skips it — nothing would ever refresh what
    is held for it. Serving it anyway would answer outside the declared reach (and grounding it can
    fail the whole request). Unreachable while one T reach is shared by every parameter (v1's single
    provider); this constructs the diverging-reach case #30 owns.
    """
    table = core_parameters()
    live = footprint_domain(STOPPED)
    stale_window = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(
                AxisName.T, Interval(_START - timedelta(days=8), _START - timedelta(days=7))
            ),
        }
    )

    class _TwoReaches(Manifold):
        def __init__(self) -> None:
            self.calls = 0

        async def project(self, selection: Selection) -> Manifold:
            self.calls += 1
            return CoverageSet((_record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0)),))

        @property
        def capability(self):  # type: ignore[no-untyped-def]
            return GranularCapability(
                reaches={
                    AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), live),
                    PRECIPITATION: (table.get(PRECIPITATION), stale_window),
                }
            )

    child = _TwoReaches()
    store = _timeline_store()
    # Precipitation is held from an earlier life, when its reach still covered this window.
    await store.assimilate(
        CoverageSet(
            (
                _record(AIR_TEMPERATURE, _native(lon=10.0, lat=20.0)),
                _record(PRECIPITATION, _native(lon=10.0, lat=20.0)),
            )
        )
    )
    reservoir = Reservoir(store, child, STOPPED)

    served = await reservoir.project(
        Selection(
            _ask(lon=10.0, lat=20.0, start=_FETCHED, end=_FETCHED + timedelta(hours=1)),
            frozenset({AIR_TEMPERATURE, PRECIPITATION}),
        )
    )

    assert isinstance(served, CoverageRecord)
    assert AIR_TEMPERATURE in served.ranges
    assert PRECIPITATION not in served.ranges  # held, but outside the reach that would refresh it
    assert child.calls == 0  # temperature was fresh; precipitation was never asked for
