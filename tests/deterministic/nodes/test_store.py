"""`MemoryStore` quantization, Holding assimilation, narration, and query behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fakes import SAMPLE_STORE, STOPPED, core_parameters, snapped_point_domain
from meteoscape.clock import StoppedClock
from meteoscape.config import StoreSpec
from meteoscape.errors import CompositionError
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import EnumerableCapability
from meteoscape.manifold.core import Selection
from meteoscape.manifold.coverage import CoverageRecord, CoverageSet
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import (
    AxisName,
    Domain,
    GridDomain,
    Interval,
    RegularAxis,
    SelectionDomain,
    SnappedAxis,
    VantageAxis,
)
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.store import MemoryStore, StoreFactory
from meteoscape.parameters import AIR_TEMPERATURE, WIND_U, ParameterId

_START = datetime(2026, 8, 9, tzinfo=UTC)
_END = datetime(2026, 8, 12, tzinfo=UTC)
_FETCHED = datetime(2026, 8, 9, 6, tzinfo=UTC)
_RETENTION = timedelta(days=14)


def _native(
    *,
    lon: float,
    lat: float,
    z: float = 2.0,
    start: datetime = _START,
    hours: int = 4,
) -> GridDomain:
    """A record's native point-forecast geometry — count-1 X/Y/Z, `hours` ticks along T."""
    return GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, lon, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, lat, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, z, 1.0, 1, False),
            AxisName.T: RegularAxis(AxisName.T, start, timedelta(hours=1), hours, False),
        }
    )


def _record(
    pid: ParameterId, domain: GridDomain, *, fetched_at: datetime = _FETCHED
) -> CoverageRecord:
    """A single-parameter, single-origin record with freely mocked provenance."""
    return CoverageRecord(
        capability=EnumerableCapability(
            domain=domain, parameters={pid: core_parameters().get(pid)}
        ),
        ranges={pid: ParameterData(values=[1.0] * len(domain), present=None)},
        provenance=Uniform(
            Provenance(
                origin=AtomicOrigin(SourceKey("fake", "default"), fetched_at),
                fetched_at=fetched_at,
                expiration=fetched_at + timedelta(hours=1),
            )
        ),
    )


def _global_grid(name: AxisName, step: float = 0.5) -> RegularAxis:
    """A whole-globe cellular lattice, the shape the factory will derive from `StoreSpec`."""
    anchor, span = (-180.0, 360.0) if name is AxisName.X else (-90.0, 180.0)
    return RegularAxis(name, anchor, step, int(span / step) + 1, cellular=True)


def _timeline_store(
    *,
    clock: StoppedClock = STOPPED,
    retention: timedelta = _RETENTION,
) -> MemoryStore:
    """The wired timeline position: X/Y latticed, T and Z spanned wholly by a Holding."""
    return MemoryStore(
        grids={AxisName.X: _global_grid(AxisName.X), AxisName.Y: _global_grid(AxisName.Y)},
        deferred=frozenset({AxisName.T, AxisName.Z}),
        clock=clock,
        retention=retention,
    )


def test_timeline_ask_defers_t_z_and_pins_containing_cell_ticks() -> None:
    """The edge's raw ask becomes the fetch-order: ANY on T/Z, the containing X/Y cells' ticks."""
    request = snapped_point_domain(start=_START, end=_END, lon=10.2, lat=45.3)

    shape = _timeline_store().quantize(request)

    assert shape.axis(AxisName.T) == SnappedAxis(AxisName.T, None)
    assert shape.axis(AxisName.Z) == SnappedAxis(AxisName.Z, None)
    # The containing cell's tick — an honest point, never the cell's span.
    assert shape.axis(AxisName.X) == RegularAxis(AxisName.X, 10.0, 0.5, 1, cellular=False)
    assert shape.axis(AxisName.Y) == RegularAxis(AxisName.Y, 45.0, 0.5, 1, cellular=False)


def test_a_tick_quantizes_to_itself() -> None:
    """A fetch order is a quantization fixed point, so point asks stay points across store hops."""
    store = _timeline_store()
    shape = store.quantize(snapped_point_domain(start=_START, end=_END, lon=10.2, lat=45.3))

    assert store.quantize(shape) == shape


def test_inverted_grid_style_store_is_the_same_fold() -> None:
    """A T-latticed store with X/Y deferred inverts the ask — no axis role is hardcoded; the
    identity arm carries the request's own Z member through."""
    store = MemoryStore(
        grids={AxisName.T: RegularAxis(AxisName.T, _START, timedelta(hours=1), 96, cellular=True)},
        deferred=frozenset({AxisName.X, AxisName.Y}),
        clock=STOPPED,
        retention=_RETENTION,
    )
    request = snapped_point_domain(
        start=_START + timedelta(minutes=30), end=_START + timedelta(hours=5, minutes=30)
    )

    shape = store.quantize(request)

    assert shape.axis(AxisName.X) == SnappedAxis(AxisName.X, None)
    assert shape.axis(AxisName.Y) == SnappedAxis(AxisName.Y, None)
    assert shape.axis(AxisName.Z) == request.axis(AxisName.Z)  # keyed by the ask
    assert shape.axis(AxisName.T) == RegularAxis(
        AxisName.T, _START, timedelta(hours=1), 6, cellular=False
    )


def test_ask_outside_the_lattice_is_declined() -> None:
    """A regional lattice has no containing cell for a far-away point — a clear refusal, not a
    silent snap to the nearest edge."""
    regional = MemoryStore(
        grids={
            AxisName.X: RegularAxis(AxisName.X, -180.0, 0.5, 10, cellular=True),
            AxisName.Y: _global_grid(AxisName.Y),
        },
        deferred=frozenset({AxisName.T, AxisName.Z}),
        clock=STOPPED,
        retention=_RETENTION,
    )
    request = snapped_point_domain(start=_START, end=_END, lon=0.0, lat=45.3)

    with pytest.raises(ValueError, match="outside the store lattice"):
        regional.quantize(request)


class _OpaqueDomain(Domain):
    """A geometry with no per-axis decomposition — the shape `quantize` cannot box."""

    def matches(self, other: Domain) -> bool:
        return False

    def intersect(self, other: Domain) -> Domain:
        raise NotImplementedError


def test_non_separable_request_is_refused() -> None:
    """The fold is per-axis; a geometry that exposes no axes cannot be translated onto boxes."""
    with pytest.raises(ValueError, match="not separable"):
        _timeline_store().quantize(_OpaqueDomain())


def test_boundary_point_reuses_clip_tolerance() -> None:
    """A point float-noise below a cell edge lands in that cell — `clip`'s index-space tolerance
    (`LATTICE_TOLERANCE`) is the one policy; `quantize` mints no second one."""
    request = snapped_point_domain(start=_START, end=_END, lon=10.0 - 1e-10, lat=45.3)

    shape = _timeline_store().quantize(request)

    assert shape.axis(AxisName.X) == RegularAxis(AxisName.X, 10.0, 0.5, 1, cellular=False)


@pytest.mark.asyncio
async def test_assimilated_answer_is_narrated_on_its_native_domain() -> None:
    """The tracer through the store core: an answer lands as a Holding, and `capability` narrates
    honest membership with the Holding's own geometry as reach."""
    store = _timeline_store()
    native = _native(lon=10.2, lat=45.3)

    await store.assimilate(CoverageSet(records=(_record(AIR_TEMPERATURE, native),)))

    assert set(store.capability.parameters) == {AIR_TEMPERATURE}
    assert store.capability.reach(AIR_TEMPERATURE) == native


def test_empty_store_advertises_no_parameters() -> None:
    assert _timeline_store().capability.parameters == {}


@pytest.mark.asyncio
async def test_multi_domain_answer_lands_keyed_by_native_z() -> None:
    """Temperature at 2 m beside wind at 10 m from one trip: each parameter's Holding keeps its own
    native geometry — the flatten ADR-0006 rejects never happens."""
    store = _timeline_store()
    at_2m = _native(lon=10.2, lat=45.3, z=2.0)
    at_10m = _native(lon=10.2, lat=45.3, z=10.0)

    await store.assimilate(
        CoverageSet(records=(_record(AIR_TEMPERATURE, at_2m), _record(WIND_U, at_10m)))
    )

    assert set(store.capability.parameters) == {AIR_TEMPERATURE, WIND_U}
    assert store.capability.reach(AIR_TEMPERATURE) == at_2m
    assert store.capability.reach(WIND_U) == at_10m


@pytest.mark.asyncio
async def test_reassimilation_replaces_the_whole_unit() -> None:
    """Same (parameter, cell, Z), new window: one Holding exists afterwards — never two windows, never
    a retained-head + fresh-tail splice. The replacement wins even with an *older* stamp, which is
    what tells whole-Holding replace apart from keep-both-narrate-latest."""
    store = _timeline_store()
    first = _native(lon=10.2, lat=45.3, start=_START, hours=4)
    shifted = _native(lon=10.2, lat=45.3, start=_START + timedelta(hours=2), hours=4)

    await store.assimilate(CoverageSet(records=(_record(AIR_TEMPERATURE, first),)))
    await store.assimilate(
        CoverageSet(
            records=(_record(AIR_TEMPERATURE, shifted, fetched_at=_FETCHED - timedelta(hours=1)),)
        )
    )

    assert store.capability.reach(AIR_TEMPERATURE) == shifted


@pytest.mark.asyncio
async def test_plural_holdings_narrate_the_latest_assimilated() -> None:
    """One parameter at two cells: membership stays honest, reach truncates to the newest Holding's
    domain (docs/adr/0007-capability-carries-its-domain.md#consequences — the per-ask exact answer is
    `project`'s, not the narration's)."""
    store = _timeline_store()
    older = _native(lon=10.2, lat=45.3)
    newer = _native(lon=20.2, lat=45.3)

    await store.assimilate(CoverageSet(records=(_record(AIR_TEMPERATURE, older),)))
    await store.assimilate(
        CoverageSet(
            records=(_record(AIR_TEMPERATURE, newer, fetched_at=_FETCHED + timedelta(hours=1)),)
        )
    )

    assert set(store.capability.parameters) == {AIR_TEMPERATURE}
    assert store.capability.reach(AIR_TEMPERATURE) == newer


def _ask(*pids: ParameterId, lon: float = 10.2, lat: float = 45.3) -> Selection:
    """A raw edge-shaped ask for the named parameters at one point."""
    return Selection(
        domain=snapped_point_domain(start=_START, end=_END, lon=lon, lat=lat),
        parameters=frozenset(pids),
    )


@pytest.mark.asyncio
async def test_cold_store_answers_an_empty_coverage_set() -> None:
    """Absence is a state, not an error — a cold store omits everything and raises nothing."""
    held = await _timeline_store().project(_ask(AIR_TEMPERATURE))

    assert isinstance(held, CoverageSet)
    assert held.records == ()
    assert held.capability.parameters == {}


@pytest.mark.asyncio
async def test_project_answers_holdings_on_their_native_domain() -> None:
    """The holdings query returns the Holding as data — native geometry and provenance intact,
    not re-shaped onto the ask."""
    store = _timeline_store()
    native = _native(lon=10.2, lat=45.3)
    record = _record(AIR_TEMPERATURE, native)
    await store.assimilate(CoverageSet(records=(record,)))

    held = await store.project(_ask(AIR_TEMPERATURE, lon=10.2, lat=45.3))

    assert len(held.records) == 1
    assert held.capability.reach(AIR_TEMPERATURE) == native
    assert held.records[0].ranges[AIR_TEMPERATURE] == record.ranges[AIR_TEMPERATURE]
    assert held.records[0].provenance.summary(AIR_TEMPERATURE) == record.provenance.summary(
        AIR_TEMPERATURE
    )


@pytest.mark.asyncio
async def test_raw_ask_and_its_fetch_order_select_the_same_holdings() -> None:
    """Translation agreement: `project` self-calls `quantize`, so a request and the refill
    fetch-order it would author hit the same boxes."""
    store = _timeline_store()
    native = _native(lon=10.2, lat=45.3)
    await store.assimilate(CoverageSet(records=(_record(AIR_TEMPERATURE, native),)))
    request = _ask(AIR_TEMPERATURE, lon=10.2, lat=45.3)
    fetch_order = Selection(domain=store.quantize(request.domain), parameters=request.parameters)

    assert await store.project(request) == await store.project(fetch_order)


@pytest.mark.asyncio
async def test_unheld_parameters_are_omitted() -> None:
    """Ask for two, hold one — the answer names only what is there; nothing raises for absence."""
    store = _timeline_store()
    await store.assimilate(
        CoverageSet(records=(_record(AIR_TEMPERATURE, _native(lon=10.2, lat=45.3)),))
    )

    held = await store.project(_ask(AIR_TEMPERATURE, WIND_U, lon=10.2, lat=45.3))

    assert set(held.capability.parameters) == {AIR_TEMPERATURE}
    assert WIND_U not in held.capability.parameters


@pytest.mark.asyncio
async def test_stale_holdings_are_returned_as_data() -> None:
    """The store is freshness-blind: an already-expired provenance travels with the Holding;
    whether to serve or refill is the reader's policy."""
    store = _timeline_store()
    expired_at = _FETCHED - timedelta(hours=2)
    native = _native(lon=10.2, lat=45.3)
    await store.assimilate(
        CoverageSet(records=(_record(AIR_TEMPERATURE, native, fetched_at=expired_at),))
    )

    held = await store.project(_ask(AIR_TEMPERATURE, lon=10.2, lat=45.3))

    assert held.capability.reach(AIR_TEMPERATURE) == native
    assert held.records[0].provenance.summary(AIR_TEMPERATURE).expiration == expired_at + timedelta(
        hours=1
    )


@pytest.mark.asyncio
async def test_project_selects_only_the_asked_cell() -> None:
    """Two cities warm two cells; an ask at one returns that Holding alone — the per-ask exact
    answer the truncating narration cannot give
    (docs/adr/0007-capability-carries-its-domain.md#consequences)."""
    store = _timeline_store()
    here = _native(lon=10.2, lat=45.3)
    there = _native(lon=20.2, lat=45.3)
    await store.assimilate(CoverageSet(records=(_record(AIR_TEMPERATURE, here),)))
    await store.assimilate(
        CoverageSet(
            records=(_record(AIR_TEMPERATURE, there, fetched_at=_FETCHED + timedelta(hours=1)),)
        )
    )

    held = await store.project(_ask(AIR_TEMPERATURE, lon=10.2, lat=45.3))

    assert held.capability.reach(AIR_TEMPERATURE) == here


@pytest.mark.asyncio
async def test_z_identity_position_matches_holdings_by_vantage_key() -> None:
    """Root-store position: Z is not deferred, so the ask's vantage cell keys the Holding —
    a different vantage misses even at the same X/Y (#25's residue, mechanized here)."""
    store = MemoryStore(
        grids={AxisName.X: _global_grid(AxisName.X), AxisName.Y: _global_grid(AxisName.Y)},
        deferred=frozenset({AxisName.T}),
        clock=STOPPED,
        retention=_RETENTION,
    )
    vantage = VantageAxis(AxisName.Z, Interval(0.0, 10.0))
    other = VantageAxis(AxisName.Z, Interval(10.0, 20.0))
    product = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 10.2, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 45.3, 1.0, 1, False),
            AxisName.Z: vantage,
            AxisName.T: RegularAxis(AxisName.T, _START, timedelta(hours=1), 4, False),
        }
    )
    await store.assimilate(CoverageSet(records=(_record(AIR_TEMPERATURE, product),)))

    def ask_at(z: VantageAxis) -> Selection:
        return Selection(
            domain=SelectionDomain(
                axes={
                    AxisName.X: RegularAxis(AxisName.X, 10.2, 1.0, 1, False),
                    AxisName.Y: RegularAxis(AxisName.Y, 45.3, 1.0, 1, False),
                    AxisName.Z: z,
                    AxisName.T: SnappedAxis(AxisName.T, Interval(_START, _END)),
                }
            ),
            parameters=frozenset({AIR_TEMPERATURE}),
        )

    hit = await store.project(ask_at(vantage))
    miss = await store.project(ask_at(other))

    assert hit.capability.reach(AIR_TEMPERATURE) == product
    assert miss.records == ()


@pytest.mark.asyncio
async def test_holdings_older_than_retention_are_evicted_on_read() -> None:
    """Housekeeping on `project`: a Holding whose `fetched_at + retention` has passed is dropped
    before the holdings query answers — never served as data."""
    now = datetime(2026, 8, 20, tzinfo=UTC)
    store = _timeline_store(clock=StoppedClock(now), retention=timedelta(days=7))
    native = _native(lon=10.2, lat=45.3)
    # fetched 10 days before `now`, retention 7 days → past the cut.
    await store.assimilate(
        CoverageSet(
            records=(_record(AIR_TEMPERATURE, native, fetched_at=now - timedelta(days=10)),)
        )
    )

    held = await store.project(_ask(AIR_TEMPERATURE, lon=10.2, lat=45.3))

    assert held.records == ()
    assert store.capability.parameters == {}


@pytest.mark.asyncio
async def test_holdings_older_than_retention_are_evicted_on_write() -> None:
    """Housekeeping on `assimilate`: inserting a fresh Holding first drops aged neighbours, so
    an already-past Holding never survives the next write."""
    now = datetime(2026, 8, 20, tzinfo=UTC)
    store = _timeline_store(clock=StoppedClock(now), retention=timedelta(days=7))
    aged = _native(lon=10.2, lat=45.3)
    fresh = _native(lon=20.2, lat=45.3)
    await store.assimilate(
        CoverageSet(records=(_record(AIR_TEMPERATURE, aged, fetched_at=now - timedelta(days=10)),))
    )
    await store.assimilate(CoverageSet(records=(_record(AIR_TEMPERATURE, fresh, fetched_at=now),)))

    held = await store.project(_ask(AIR_TEMPERATURE, lon=10.2, lat=45.3))
    kept = await store.project(_ask(AIR_TEMPERATURE, lon=20.2, lat=45.3))

    assert held.records == ()
    assert kept.capability.reach(AIR_TEMPERATURE) == fresh


def test_factory_builds_global_xy_lattices_from_spatial_step() -> None:
    """The factory owns `StoreSpec` → lattice derivation: a 0.5° step covers the closed globe
    with cellular X/Y, and the store's quantize then pins containing ticks."""
    store = StoreFactory(STOPPED).create(
        StoreSpec(spatial_step=0.5, retention_interval=_RETENTION),
        frozenset({AxisName.T, AxisName.Z}),
    )
    assert isinstance(store, MemoryStore)

    shape = store.quantize(snapped_point_domain(start=_START, end=_END, lon=10.2, lat=45.3))

    assert shape.axis(AxisName.X) == RegularAxis(AxisName.X, 10.0, 0.5, 1, cellular=False)
    assert shape.axis(AxisName.Y) == RegularAxis(AxisName.Y, 45.0, 0.5, 1, cellular=False)
    assert shape.axis(AxisName.T) == SnappedAxis(AxisName.T, None)
    assert shape.axis(AxisName.Z) == SnappedAxis(AxisName.Z, None)


def test_factory_remembers_every_store_it_allocated() -> None:
    """The composition root releases what the graph opened, and the factory is the only place a
    store is built — so it, not the woven graph, is where the roster comes from."""
    factory = StoreFactory(STOPPED)
    source_store = factory.create(SAMPLE_STORE, frozenset({AxisName.T}))
    root_store = factory.create(SAMPLE_STORE, frozenset({AxisName.T, AxisName.Z}))
    assert factory.created == (source_store, root_store)


@pytest.mark.parametrize("step", [0.0, -0.1, 90.1])
def test_factory_rejects_spatial_step_outside_open_closed_unit_interval(step: float) -> None:
    """Build-time refusal: `0 < step ≤ 90`, else the globe lattice is unbuildable."""
    with pytest.raises(CompositionError, match="spatial_step"):
        StoreFactory(STOPPED).create(
            StoreSpec(spatial_step=step, retention_interval=_RETENTION),
            frozenset({AxisName.T}),
        )


def test_factory_honours_position_deferred_axes() -> None:
    """Product position defers only T — Z passes identity through quantize."""
    store = StoreFactory(STOPPED).create(SAMPLE_STORE, frozenset({AxisName.T}))
    request = snapped_point_domain(start=_START, end=_END, lon=10.2, lat=45.3)

    shape = store.quantize(request)

    assert shape.axis(AxisName.T) == SnappedAxis(AxisName.T, None)
    assert shape.axis(AxisName.Z) == request.axis(AxisName.Z)
