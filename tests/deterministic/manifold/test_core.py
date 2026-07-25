"""`Countable` is a result-only facet: a `Coverage` is Countable; no node is."""

from __future__ import annotations

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
from meteoscape.nodes.reservoir import Reservoir
from meteoscape.nodes.store import StubStore
from meteoscape.parameters import AIR_TEMPERATURE


def _fake_provider() -> FakeProvider:
    capability = footprint_capability(STOPPED, core_parameters(), frozenset({AIR_TEMPERATURE}))
    return FakeProvider(source_key=SourceKey("fake", "default"), capability=capability)


def test_nodes_are_not_countable() -> None:
    provider = _fake_provider()
    store = StubStore()
    reservoir = Reservoir(store, provider)
    assert not isinstance(store, Countable)
    assert not isinstance(reservoir, Countable)
    assert not isinstance(provider, Countable)


def test_coverage_is_countable() -> None:
    assert isinstance(coverage_record(AIR_TEMPERATURE, domain=sample_lattice(count=1)), Countable)
