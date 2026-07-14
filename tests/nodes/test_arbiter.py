"""Arbiter — priority ranking + Phase C admission / single-candidate projection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fakes import (
    SAMPLE_STORE,
    STOPPED,
    FakeProvider,
    air_temperature_capability,
    core_parameters,
    fake_catalog,
    point_timeline_domain,
)
from meteoscape.config import ArbiterPolicy, OfferingDef
from meteoscape.errors import CapabilityMismatch
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import EnumerableCapability, FootprintCapability
from meteoscape.manifold.core import Manifold, Selection
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import (
    AxisName,
    ContinuousAxis,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
)
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.arbiter import Arbiter
from meteoscape.nodes.composition import (
    CompositionError,
    RegisteredSource,
    SourceBinder,
    SourceRegistry,
)
from meteoscape.nodes.providers.base import Provider
from meteoscape.nodes.reservoir import Reservoir
from meteoscape.nodes.store import StoreFactory
from meteoscape.parameters import AIR_TEMPERATURE, PRECIPITATION


def _bind(*offerings: OfferingDef, catalog=None):
    catalog = catalog or fake_catalog()
    return SourceBinder(catalog).build(
        list(offerings), secrets={}, clock=STOPPED, parameters=core_parameters()
    )


def _source_nodes(registry):
    stores = StoreFactory()
    return {
        key: Reservoir(
            stores.create(reg.store if reg.store is not None else reg.provider.domain),
            reg.provider,
        )
        for key, reg in registry.sources.items()
    }


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


def _coverage(*pids) -> CoverageRecord:
    table = core_parameters()
    domain = point_timeline_domain(hours=1, lon=13.41, lat=52.52)
    parameters = {pid: table.get(pid) for pid in pids}
    return CoverageRecord(
        capability=EnumerableCapability(domain=domain, parameters=parameters),
        ranges={pid: ParameterData(values=[1.0], present=None) for pid in pids},
        provenance=Uniform(
            Provenance(
                origin=AtomicOrigin(SourceKey("fake", "default"), datetime(2026, 7, 11, tzinfo=UTC)),
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
    arbiter = Arbiter(_source_nodes(registry), registry, ArbiterPolicy())
    candidates = arbiter.candidates[AIR_TEMPERATURE]
    assert len(candidates) == 2
    first, second = candidates
    assert isinstance(first, Reservoir) and isinstance(second, Reservoir)
    assert isinstance(first.source, Provider) and isinstance(second.source, Provider)
    assert first.source.source_key.provider == "b"
    assert second.source.source_key.provider == "a"


def test_unsupported_reconciler_raises() -> None:
    registry = _bind(OfferingDef(impl="fake", name="default", priority=0))
    with pytest.raises(CompositionError, match="reconciler"):
        Arbiter(
            _source_nodes(registry),
            registry,
            ArbiterPolicy(default_reconciler="consensus"),
        )


def test_empty_registry_empty_candidates() -> None:
    registry = SourceRegistry(sources={})
    arbiter = Arbiter({}, registry, ArbiterPolicy())
    assert arbiter.candidates == {}
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
    arbiter = Arbiter(_source_nodes(registry), registry, ArbiterPolicy())
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
    arbiter = Arbiter(_source_nodes(registry), registry, ArbiterPolicy())
    selection = _point_selection(parameters=frozenset({AIR_TEMPERATURE, PRECIPITATION}))
    result = await arbiter.project(selection)
    assert result is coverage
    assert len(provider.calls) == 1
    assert provider.calls[0].domain is selection.domain
    assert provider.calls[0].parameters == frozenset({AIR_TEMPERATURE})


@pytest.mark.asyncio
async def test_different_winning_candidates_guard() -> None:
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
    temp_provider = _RecordingProvider(
        source_key=SourceKey("a", "default"),
        capability=FootprintCapability(
            footprints={AIR_TEMPERATURE: (table.get(AIR_TEMPERATURE), footprint)}
        ),
        coverage=_coverage(AIR_TEMPERATURE),
    )
    precip_provider = _RecordingProvider(
        source_key=SourceKey("b", "default"),
        capability=FootprintCapability(
            footprints={PRECIPITATION: (table.get(PRECIPITATION), footprint)}
        ),
        coverage=_coverage(PRECIPITATION),
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
    arbiter = Arbiter(_source_nodes(registry), registry, ArbiterPolicy())
    with pytest.raises(NotImplementedError, match="005"):
        await arbiter.project(
            _point_selection(parameters=frozenset({AIR_TEMPERATURE, PRECIPITATION}))
        )
    assert temp_provider.calls == []
    assert precip_provider.calls == []
