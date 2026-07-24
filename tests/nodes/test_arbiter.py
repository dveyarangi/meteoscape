"""Arbiter — Producer + PriorityReconciler + admission / single-winner projection."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import pytest

from fakes import (
    SAMPLE_STORE,
    STOPPED,
    FakeProvider,
    air_temperature_capability,
    core_parameters,
    fake_catalog,
    footprint_domain,
    point_timeline_domain,
)
from meteoscape.config import ArbiterPolicy, OfferingDef
from meteoscape.errors import CapabilityMismatch
from meteoscape.identity import ProducerKey, SourceKey
from meteoscape.manifold.cadence import CadenceDef
from meteoscape.manifold.capability import EnumerableCapability, FootprintCapability
from meteoscape.manifold.core import Countable, Manifold, Selection
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import (
    AxisName,
    ContinuousAxis,
    Domain,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
)
from meteoscape.manifold.provenance import AtomicOrigin, PerParameter, Provenance, Uniform
from meteoscape.nodes.arbiter import Arbiter, PriorityReconciler, Producer, build_reconciler
from meteoscape.nodes.composition import (
    CalculatorRegistry,
    CompositionError,
    RegisteredSource,
    SourceBinder,
    SourceRegistry,
)
from meteoscape.nodes.providers.base import Provider
from meteoscape.nodes.reservoir import Reservoir
from meteoscape.nodes.store import StoreFactory
from meteoscape.parameters import AIR_TEMPERATURE, PRECIPITATION, ParameterId


def _bind(*offerings: OfferingDef, catalog=None):
    catalog = catalog or fake_catalog()
    return SourceBinder(catalog).build(
        list(offerings), secrets={}, clock=STOPPED, parameters=core_parameters()
    )


def _producers(registry: SourceRegistry) -> list[Producer]:
    stores = StoreFactory()
    producers: list[Producer] = []
    for key, reg in registry.sources.items():
        if reg.store is not None:
            spec = reg.store
        else:
            # A provider-exact lattice is the `Countable` facet, not the `Provider` base — mirrors
            # the narrowing `weaver._source_grid` does in production.
            assert isinstance(reg.provider, Countable)
            spec = reg.provider.domain
        producers.append(Producer(node=Reservoir(stores.create(spec), reg.provider), key=key))
    return producers


def _arbiter(
    registry: SourceRegistry,
    *,
    policy: ArbiterPolicy | None = None,
    producers: list[Producer] | None = None,
) -> Arbiter:
    producers = producers if producers is not None else _producers(registry)
    reconciler = build_reconciler(
        policy or ArbiterPolicy(),
        registry,
        CalculatorRegistry(calculators={}),
    )
    return Arbiter(producers, reconciler)


def _point_selection(
    *,
    lon: float = 13.41,
    lat: float = 52.52,
    z: float = 0.0,
    parameters: frozenset = frozenset({AIR_TEMPERATURE}),
) -> Selection:
    return Selection(
        domain=GridDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, lon, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, lat, 1.0, 1, False),
                AxisName.Z: RegularAxis(AxisName.Z, z, 1.0, 1, False),
                AxisName.T: RegularAxis(
                    AxisName.T,
                    datetime(2026, 7, 11, 12, tzinfo=UTC),
                    timedelta(hours=1),
                    2,
                    True,
                ),
            }
        ),
        parameters=parameters,
    )


def _coverage(*pids, origin_key: SourceKey | None = None) -> CoverageRecord:
    table = core_parameters()
    domain = point_timeline_domain(hours=1, lon=13.41, lat=52.52)
    parameters = {pid: table.get(pid) for pid in pids}
    key = origin_key or SourceKey("fake", "default")
    return CoverageRecord(
        capability=EnumerableCapability(domain=domain, parameters=parameters),
        ranges={pid: ParameterData(values=[1.0], present=None) for pid in pids},
        provenance=Uniform(
            Provenance(
                origin=AtomicOrigin(key, datetime(2026, 7, 11, tzinfo=UTC)),
                fetched_at=datetime(2026, 7, 11, 12, tzinfo=UTC),
                expiration=datetime(2026, 7, 11, 13, tzinfo=UTC),
            )
        ),
    )


class _RecordingProvider(FakeProvider):
    def __init__(self, *, source_key: SourceKey, capability, coverage: CoverageRecord) -> None:
        super().__init__(source_key=source_key, capability=capability)
        self.calls: list[Selection] = []
        self._coverage = coverage

    async def project(self, selection: Selection) -> Manifold:
        self.calls.append(selection)
        return self._coverage


def test_priority_reconciler_orders_candidates() -> None:
    catalog = {
        **fake_catalog(impl_id="a", provider_id="a"),
        **fake_catalog(impl_id="b", provider_id="b"),
    }
    registry = _bind(
        OfferingDef(impl="a", name="default", priority=1),
        OfferingDef(impl="b", name="default", priority=0),
        catalog=catalog,
    )
    arbiter = _arbiter(registry)
    ordered = arbiter.reconciler.select(AIR_TEMPERATURE, arbiter.by_parameter[AIR_TEMPERATURE])
    assert len(ordered) == 2
    first, second = ordered
    assert isinstance(first.node, Reservoir) and isinstance(second.node, Reservoir)
    assert isinstance(first.node.source, Provider) and isinstance(second.node.source, Provider)
    # `ProducerKey` is a union — only a `SourceKey` carries a provider.
    assert isinstance(first.key, SourceKey) and isinstance(second.key, SourceKey)
    assert first.key.provider == "b"
    assert second.key.provider == "a"


def test_unsupported_reconciler_raises() -> None:
    registry = _bind(OfferingDef(impl="fake", name="default", priority=0))
    with pytest.raises(CompositionError, match="reconciler"):
        build_reconciler(
            ArbiterPolicy(default_reconciler="consensus"),
            registry,
            CalculatorRegistry(calculators={}),
        )


def test_empty_registry_empty_index() -> None:
    registry = SourceRegistry(sources={})
    arbiter = _arbiter(registry, producers=[])
    assert arbiter.by_parameter == {}
    assert arbiter.capability.parameters == {}


@pytest.mark.asyncio
async def test_beyond_footprint_raises_without_projecting() -> None:
    coverage = _coverage(AIR_TEMPERATURE)
    provider = _RecordingProvider(
        source_key=SourceKey("fake", "default"),
        capability=air_temperature_capability(STOPPED, core_parameters()),
        coverage=coverage,
    )
    key = provider.source_key
    registry = SourceRegistry(
        sources={key: RegisteredSource(provider=provider, priority=0, store=SAMPLE_STORE)}
    )
    arbiter = _arbiter(registry)
    with pytest.raises(CapabilityMismatch):
        await arbiter.project(_point_selection(lat=100.0))  # outside Y footprint
    assert provider.calls == []


@pytest.mark.asyncio
async def test_in_footprint_projects_once_with_admitted_params() -> None:
    coverage = _coverage(AIR_TEMPERATURE)
    provider = _RecordingProvider(
        source_key=SourceKey("fake", "default"),
        capability=air_temperature_capability(STOPPED, core_parameters()),
        coverage=coverage,
    )
    key = provider.source_key
    registry = SourceRegistry(
        sources={key: RegisteredSource(provider=provider, priority=0, store=SAMPLE_STORE)}
    )
    arbiter = _arbiter(registry)
    selection = _point_selection(parameters=frozenset({AIR_TEMPERATURE, PRECIPITATION}))
    result = await arbiter.project(selection)
    assert result is coverage
    assert len(provider.calls) == 1
    assert provider.calls[0].domain is selection.domain
    assert provider.calls[0].parameters == frozenset({AIR_TEMPERATURE})


@pytest.mark.asyncio
async def test_assembles_disjoint_winners_into_per_parameter_coverage() -> None:
    table = core_parameters()
    footprint = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(
                AxisName.T,
                Interval(datetime(2026, 7, 1, tzinfo=UTC), datetime(2026, 8, 1, tzinfo=UTC)),
            ),
        }
    )
    temp_cov = _coverage(AIR_TEMPERATURE, origin_key=SourceKey("a", "default"))
    precip_cov = _coverage(PRECIPITATION, origin_key=SourceKey("b", "default"))
    temp_provider = _RecordingProvider(
        source_key=SourceKey("a", "default"),
        capability=FootprintCapability(
            footprints={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), footprint)}
        ),
        coverage=temp_cov,
    )
    precip_provider = _RecordingProvider(
        source_key=SourceKey("b", "default"),
        capability=FootprintCapability(
            footprints={PRECIPITATION: (table.get(PRECIPITATION), footprint)}
        ),
        coverage=precip_cov,
    )
    registry = SourceRegistry(
        sources={
            temp_provider.source_key: RegisteredSource(
                provider=temp_provider, priority=0, store=SAMPLE_STORE
            ),
            precip_provider.source_key: RegisteredSource(
                provider=precip_provider, priority=1, store=SAMPLE_STORE
            ),
        }
    )
    arbiter = _arbiter(registry)
    selection = _point_selection(parameters=frozenset({AIR_TEMPERATURE, PRECIPITATION}))
    result = await arbiter.project(selection)

    assert isinstance(result, CoverageRecord)
    assert set(result.ranges) == {AIR_TEMPERATURE, PRECIPITATION}
    assert result.ranges[AIR_TEMPERATURE] is temp_cov.ranges[AIR_TEMPERATURE]
    assert result.ranges[PRECIPITATION] is precip_cov.ranges[PRECIPITATION]
    assert result.domain == temp_cov.domain == precip_cov.domain
    assert isinstance(result.provenance, PerParameter)
    temp_origin = result.provenance.summary(AIR_TEMPERATURE).origin
    precip_origin = result.provenance.summary(PRECIPITATION).origin
    assert isinstance(temp_origin, AtomicOrigin)
    assert isinstance(precip_origin, AtomicOrigin)
    assert temp_origin.source == SourceKey("a", "default")
    assert precip_origin.source == SourceKey("b", "default")
    assert len(temp_provider.calls) == 1
    assert len(precip_provider.calls) == 1
    assert temp_provider.calls[0].parameters == frozenset({AIR_TEMPERATURE})
    assert precip_provider.calls[0].parameters == frozenset({PRECIPITATION})


# --- compose_domains: the reconciler's domain composition (Stage 2, ADR-0007) ---

_T0 = datetime(2026, 7, 11, 12, tzinfo=UTC)


def _global(*, days: int) -> FootprintDomain:
    return FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(_T0, _T0 + timedelta(days=days))),
        }
    )


def _box(*, x: Interval[float], days: int = 10) -> FootprintDomain:
    return FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, x),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(_T0, _T0 + timedelta(days=days))),
        }
    )


def _pkey(dataset: str) -> SourceKey:
    return SourceKey(provider="test", dataset=dataset)


def _reconciler() -> PriorityReconciler:
    return PriorityReconciler(priority={})


class _NonSeparable(Domain):
    """Curvilinear stand-in: satisfies `Domain`, exposes no axes (concern #12, source role)."""

    def matches(self, other: Domain) -> bool:
        return False

    def intersect(self, other: Domain) -> Domain:
        return self


def test_compose_domains_single_candidate_returns_itself() -> None:
    domain = _global(days=10)
    assert _reconciler().compose_domains(AIR_TEMPERATURE, [(_pkey("a"), domain)]) is domain


def test_compose_domains_returns_dominating_reach() -> None:
    short = _global(days=10)
    long = _global(days=16)
    result = _reconciler().compose_domains(
        AIR_TEMPERATURE, [(_pkey("short"), short), (_pkey("long"), long)]
    )
    assert result is long


def test_compose_domains_equal_extent_tie_returns_one_input() -> None:
    left = _global(days=10)
    right = _global(days=10)
    assert left is not right
    result = _reconciler().compose_domains(
        AIR_TEMPERATURE, [(_pkey("a"), left), (_pkey("b"), right)]
    )
    assert result is left or result is right


@pytest.mark.parametrize(
    "priority",
    [{}, {SourceKey("test", "short"): 0, SourceKey("test", "long"): 9}],
)
def test_compose_domains_ignores_priority(priority: Mapping[ProducerKey, int]) -> None:
    """Dominance is geometric — the widest wins whatever priority says (004 shape)."""
    short = _global(days=10)
    long = _global(days=16)
    result = PriorityReconciler(priority=priority).compose_domains(
        AIR_TEMPERATURE, [(_pkey("short"), short), (_pkey("long"), long)]
    )
    assert result is long


def test_compose_domains_incomparable_names_parameter_producers_and_both_axes() -> None:
    """`Global x 10 d` vs `Europe x 16 d`: global wins x, europe wins t — report both, and the param."""
    glob = _box(x=Interval(-180.0, 180.0), days=10)
    europe = _box(x=Interval(-10.0, 40.0), days=16)
    with pytest.raises(CompositionError) as exc:
        _reconciler().compose_domains(
            AIR_TEMPERATURE, [(_pkey("global"), glob), (_pkey("europe"), europe)]
        )
    message = str(exc.value)
    assert "air_temperature" in message
    assert "test:global extends beyond test:europe on x" in message
    assert "test:europe extends beyond test:global on t" in message


def test_compose_domains_rejects_non_separable_multi_candidate() -> None:
    with pytest.raises(CompositionError) as exc:
        _reconciler().compose_domains(
            AIR_TEMPERATURE,
            [(_pkey("swath"), _NonSeparable()), (_pkey("grid"), _global(days=10))],
        )
    message = str(exc.value)
    assert "air_temperature" in message
    assert "test:swath" in message
    assert "separable" in message.lower()
    assert "unbuilt" not in message


def test_compose_domains_lone_non_separable_returned_unchanged() -> None:
    """Defect 3: a single curvilinear candidate compares against nothing, so it builds."""
    swath = _NonSeparable()
    assert _reconciler().compose_domains(AIR_TEMPERATURE, [(_pkey("swath"), swath)]) is swath


def test_compose_domains_empty_raises() -> None:
    with pytest.raises(CompositionError, match="air_temperature"):
        _reconciler().compose_domains(AIR_TEMPERATURE, [])


# --- Stage 3: the Arbiter composes reach eagerly at construction (ADR-0007) ---


class _AdvancingClock:
    """Mutable clock for liveness — advance `instant` and RollingAxis extents move."""

    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant


def _footprint_leaf(key: SourceKey, domain: FootprintDomain) -> Producer:
    """A single-parameter (AIR_TEMPERATURE) footprint producer behind a Reservoir."""
    table = core_parameters()
    capability = FootprintCapability(
        footprints={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), domain)}
    )
    provider = FakeProvider(source_key=key, capability=capability)
    return Producer(node=Reservoir(StoreFactory().create(SAMPLE_STORE), provider), key=key)


def test_arbiter_publishes_the_dominating_reach() -> None:
    short = _global(days=10)
    long = _global(days=16)
    arbiter = Arbiter(
        [
            _footprint_leaf(SourceKey("short", "default"), short),
            _footprint_leaf(SourceKey("long", "default"), long),
        ],
        PriorityReconciler(priority={}),
    )
    assert arbiter.capability.reach(AIR_TEMPERATURE) is long


def test_arbiter_incomparable_reach_raises_at_construction() -> None:
    glob = _box(x=Interval(-180.0, 180.0), days=10)
    europe = _box(x=Interval(-10.0, 40.0), days=16)
    with pytest.raises(CompositionError, match="air_temperature"):
        Arbiter(
            [
                _footprint_leaf(SourceKey("global", "default"), glob),
                _footprint_leaf(SourceKey("europe", "default"), europe),
            ],
            PriorityReconciler(priority={}),
        )


def test_arbiter_capability_is_one_stored_object() -> None:
    arbiter = Arbiter(
        [_footprint_leaf(SourceKey("only", "default"), _global(days=10))],
        PriorityReconciler(priority={}),
    )
    assert arbiter.capability is arbiter.capability


def test_arbiter_reach_is_the_childs_live_object() -> None:
    """The composed reach is a candidate's own `Domain` (`is`), so a clock-anchored `RollingAxis`
    stays live — advancing the clock moves the published extent, proving no snapshot copy."""
    clock = _AdvancingClock(datetime(2026, 7, 11, 12, tzinfo=UTC))
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(0),
        max_lead=timedelta(days=7),
    )
    footprint = footprint_domain(clock, cadence=cadence)
    arbiter = Arbiter(
        [_footprint_leaf(SourceKey("live", "default"), footprint)],
        PriorityReconciler(priority={}),
    )
    reach = arbiter.capability.reach(AIR_TEMPERATURE)
    assert reach is footprint
    assert isinstance(reach, FootprintDomain)
    before = reach.axis(AxisName.T).extent.upper
    clock.instant = clock.instant + timedelta(days=1)
    assert reach.axis(AxisName.T).extent.upper == before + timedelta(days=1)


def test_reservoir_forwards_child_reach_unchanged() -> None:
    """The root is `Reservoir(store, Arbiter)`; forwarding the child's reach carries the root's."""
    domain = _global(days=10)
    table = core_parameters()
    capability = FootprintCapability(
        footprints={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), domain)}
    )
    provider = FakeProvider(source_key=SourceKey("src", "default"), capability=capability)
    reservoir = Reservoir(StoreFactory().create(SAMPLE_STORE), provider)
    assert reservoir.capability.reach(AIR_TEMPERATURE) is domain


# --- Stage 4: a scoped Arbiter declares exactly its scope (ADR-0007 defect 1) ---


def _multi_producer(key: SourceKey, footprints: Mapping[ParameterId, FootprintDomain]) -> Producer:
    """A producer serving several parameters, each on its own footprint."""
    table = core_parameters()
    capability = FootprintCapability(
        footprints={pid: (table.get(pid), dom) for pid, dom in footprints.items()}
    )
    provider = FakeProvider(source_key=key, capability=capability)
    return Producer(node=Reservoir(StoreFactory().create(SAMPLE_STORE), provider), key=key)


def _europe_vs_americas() -> list[Producer]:
    """Two producers agreeing on AIR_TEMPERATURE (global) but incomparable on PRECIPITATION."""
    return [
        _multi_producer(
            SourceKey("a", "default"),
            {AIR_TEMPERATURE: _global(days=10), PRECIPITATION: _box(x=Interval(-10.0, 40.0))},
        ),
        _multi_producer(
            SourceKey("b", "default"),
            {AIR_TEMPERATURE: _global(days=10), PRECIPITATION: _box(x=Interval(-140.0, -60.0))},
        ),
    ]


def test_scoped_arbiter_declares_exactly_its_scope() -> None:
    """A scoped resolver composes and declares only its scope, never a whole producer's out-of-scope
    parameter — so incomparable out-of-scope footprints cannot shear the build."""
    arbiter = Arbiter(
        _europe_vs_americas(), PriorityReconciler(priority={}), scope=frozenset({AIR_TEMPERATURE})
    )
    assert set(arbiter.capability.parameters) == {AIR_TEMPERATURE}
    assert isinstance(arbiter.capability.reach(AIR_TEMPERATURE), FootprintDomain)
    with pytest.raises(KeyError):
        arbiter.capability.reach(PRECIPITATION)


def test_unscoped_arbiter_over_declares_and_shears_on_incomparable() -> None:
    """The defect scope fixes: unscoped, the same Arbiter composes PRECIPITATION too and shears."""
    with pytest.raises(CompositionError, match="precipitation"):
        Arbiter(_europe_vs_americas(), PriorityReconciler(priority={}))
