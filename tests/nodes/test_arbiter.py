"""Arbiter — registry + source map; priority reconciler owns ranking."""

from __future__ import annotations

import pytest

from fakes import STOPPED, core_parameters, fake_catalog
from meteoscape.config import ArbiterPolicy, OfferingDef
from meteoscape.nodes.arbiter import Arbiter
from meteoscape.nodes.composition import CompositionError, SourceBinder, SourceRegistry
from meteoscape.nodes.providers.base import Provider
from meteoscape.nodes.reservoir import Reservoir
from meteoscape.nodes.store import StoreFactory
from meteoscape.parameters import AIR_TEMPERATURE


def _bind(*offerings: OfferingDef, catalog=None):
    catalog = catalog or fake_catalog()
    return SourceBinder(catalog).build(
        list(offerings), secrets={}, clock=STOPPED, parameters=core_parameters()
    )


def _source_nodes(registry):
    stores = StoreFactory()
    return {
        key: Reservoir(stores.create(reg.source_lattice), reg.provider)
        for key, reg in registry.sources.items()
    }


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
