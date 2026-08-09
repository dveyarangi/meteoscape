"""`Countable` is a result-only facet: a `Coverage` is Countable; no node is."""

from __future__ import annotations

from datetime import timedelta

from fakes import (
    STOPPED,
    FakeProvider,
    core_parameters,
    coverage_record,
    footprint_capability,
    sample_lattice,
)
from meteoscape.identity import SourceKey
from meteoscape.manifold.core import Countable
from meteoscape.manifold.domain import AxisName, RegularAxis
from meteoscape.nodes.reservoir import Reservoir
from meteoscape.nodes.store import MemoryStore
from meteoscape.parameters import AIR_TEMPERATURE


def _fake_provider() -> FakeProvider:
    capability = footprint_capability(STOPPED, core_parameters(), frozenset({AIR_TEMPERATURE}))
    return FakeProvider(source_key=SourceKey("fake", "default"), capability=capability)


def test_nodes_are_not_countable() -> None:
    provider = _fake_provider()
    store = MemoryStore(
        grids={
            AxisName.X: RegularAxis(AxisName.X, -180.0, 1.0, 1, cellular=True),
            AxisName.Y: RegularAxis(AxisName.Y, -90.0, 1.0, 1, cellular=True),
        },
        deferred=frozenset({AxisName.T, AxisName.Z}),
        clock=STOPPED,
        retention=timedelta(days=14),
    )
    reservoir = Reservoir(store, provider, STOPPED)
    assert not isinstance(store, Countable)
    assert not isinstance(reservoir, Countable)
    assert not isinstance(provider, Countable)


def test_coverage_is_countable() -> None:
    assert isinstance(coverage_record(AIR_TEMPERATURE, domain=sample_lattice(count=1)), Countable)
