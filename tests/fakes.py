"""Shared test doubles for the composition / weave seam."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from meteoscape.clock import Clock, StoppedClock
from meteoscape.config import StoreSpec
from meteoscape.identity import SourceKey
from meteoscape.manifold.cadence import CadenceDef, RollingAxis
from meteoscape.manifold.capability import Capability, FootprintCapability
from meteoscape.manifold.core import Manifold, Selection
from meteoscape.manifold.domain import (
    AxisName,
    ContinuousAxis,
    EnumerableDomain,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
)
from meteoscape.nodes.catalog.paramtable import ParameterTable, StaticParameterTable
from meteoscape.nodes.catalog.providers import (
    OfferingSpec,
    ProviderCatalog,
    ProviderManifest,
    SecretSlot,
)
from meteoscape.nodes.providers.base import Provider
from meteoscape.nodes.store import Store, StoreFactory
from meteoscape.parameters import AIR_TEMPERATURE, ParameterId

STOPPED = StoppedClock(datetime(2026, 7, 11, 12, 0, tzinfo=UTC))

_CADENCE = CadenceDef(
    cadence=timedelta(hours=1),
    publication_latency=timedelta(0),
    max_lead=timedelta(days=7),
)

SAMPLE_STORE = StoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14))


def sample_lattice(*, count: int = 1) -> GridDomain:
    """A constructible enumerable lattice (all axes share `count`)."""
    return GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, count, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, count, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, count, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), count, False
            ),
        }
    )


def point_timeline_domain(*, hours: int = 4, lon: float = 1.0, lat: float = 2.0) -> GridDomain:
    """Count-1 spatial + Z axes; `hours` ticks along T (the v1 point-forecast shape)."""
    return GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, lon, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, lat, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), hours, False
            ),
        }
    )


def footprint_domain(
    clock: Clock = STOPPED,
    *,
    cadence: CadenceDef | None = None,
) -> FootprintDomain:
    """A global continuous footprint with a clock-anchored rolling `valid_time`."""
    return FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: RollingAxis(AxisName.T, cadence or _CADENCE, clock),
        }
    )


def _footprint(clock: Clock) -> FootprintDomain:
    return footprint_domain(clock)


def air_temperature_capability(clock: Clock, parameters: ParameterTable) -> FootprintCapability:
    definition = parameters.get(AIR_TEMPERATURE)
    return FootprintCapability(footprints={definition.id: (definition, _footprint(clock))})


def footprint_capability(
    clock: Clock, parameters: ParameterTable, pids: frozenset[ParameterId]
) -> FootprintCapability:
    footprint = _footprint(clock)
    return FootprintCapability(footprints={pid: (parameters.get(pid), footprint) for pid in pids})


class FakeProvider(Provider):
    """Test fixture leaf — declared capability + source_key; `project` raises. Not Countable."""

    def __init__(self, *, source_key: SourceKey, capability: Capability) -> None:
        self._source_key = source_key
        self._capability = capability

    async def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError("FakeProvider has no project face")

    @property
    def capability(self) -> Capability:
        return self._capability

    @property
    def source_key(self) -> SourceKey:
        return self._source_key


class CountableFakeProvider(FakeProvider):
    """Countable fake — lattice resolution prefers `provider.domain`."""

    def __init__(
        self,
        *,
        source_key: SourceKey,
        capability: Capability,
        domain: EnumerableDomain,
    ) -> None:
        super().__init__(source_key=source_key, capability=capability)
        self._domain = domain

    @property
    def domain(self) -> EnumerableDomain:
        return self._domain


class RecordingStoreFactory(StoreFactory):
    """Records each `create` call; delegates allocation to `StoreFactory`."""

    def __init__(self) -> None:
        self.calls: list[EnumerableDomain | StoreSpec | None] = []

    def create(self, grid: EnumerableDomain | StoreSpec | None) -> Store:
        self.calls.append(grid)
        return super().create(grid)


def fake_catalog(
    *,
    impl_id: str = "fake",
    provider_id: str = "fake",
    offerings: Mapping[str, OfferingSpec] | None = None,
    countable: bool = False,
    secret: SecretSlot | None = None,
    built: list[tuple[OfferingSpec, Mapping[str, object], str | None]] | None = None,
) -> ProviderCatalog:
    """One-impl catalogue whose `build` yields a fake serving air temperature."""

    record = built if built is not None else []
    specs = offerings or {
        "default": OfferingSpec(
            name="default",
            parameters=frozenset({AIR_TEMPERATURE}),
            store=None if countable else SAMPLE_STORE,
        )
    }

    def build(
        spec: OfferingSpec,
        settings: Mapping[str, object],
        secret_value: str | None,
        clock: Clock,
        parameters: ParameterTable,
    ) -> Provider:
        record.append((spec, settings, secret_value))
        key = SourceKey(provider=provider_id, dataset=spec.name)
        capability = footprint_capability(clock, parameters, spec.parameters)
        if countable:
            return CountableFakeProvider(
                source_key=key, capability=capability, domain=sample_lattice(count=2)
            )
        return FakeProvider(source_key=key, capability=capability)

    return {
        impl_id: ProviderManifest(
            impl_id=impl_id,
            provider_id=provider_id,
            offerings=specs,
            secret=secret,
            build=build,
        )
    }


def core_parameters() -> StaticParameterTable:
    return StaticParameterTable.core()
