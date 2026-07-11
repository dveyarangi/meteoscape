"""Weaver — allocate stores, build Source map, hand registry to Arbiter."""

from __future__ import annotations

from datetime import timedelta

import pytest

from fakes import STOPPED, RecordingStoreFactory, core_parameters, fake_catalog
from meteoscape.config import ArbiterPolicy, OfferingDef, RootStoreSpec
from meteoscape.nodes.arbiter import Arbiter
from meteoscape.nodes.catalog.calculators import CalculatorManifest
from meteoscape.nodes.composition import (
    CalculatorRegistry,
    ProfileDef,
    RegisteredCalculator,
    SourceBinder,
    SourceRegistry,
)
from meteoscape.nodes.reservoir import Reservoir
from meteoscape.nodes.weaver import Weaver
from meteoscape.parameters import AIR_TEMPERATURE, WIND_SPEED, WIND_U, WIND_V


def _root_store() -> RootStoreSpec:
    return RootStoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14))


def _profile(
    *,
    offerings: list[OfferingDef],
    catalog=None,
    calculators: CalculatorRegistry | None = None,
    arbiter: ArbiterPolicy | None = None,
) -> ProfileDef:
    catalog = catalog or fake_catalog()
    sources = SourceBinder(catalog).build(
        offerings, secrets={}, clock=STOPPED, parameters=core_parameters()
    )
    return ProfileDef(
        sources=sources,
        calculators=calculators or CalculatorRegistry(calculators={}),
        root_store=_root_store(),
        arbiter=arbiter or ArbiterPolicy(),
    )


def test_single_source_weaves_capability_and_stores() -> None:
    stores = RecordingStoreFactory()
    profile = _profile(offerings=[OfferingDef(impl="fake", name="default", priority=0)])
    root = Weaver(stores).weave(profile)

    assert isinstance(root, Reservoir)
    assert AIR_TEMPERATURE in root.capability.parameters
    assert len(stores.calls) == 2
    source_lattice = next(iter(profile.sources.sources.values())).source_lattice
    assert stores.calls[0] is source_lattice
    assert stores.calls[1] is None
    assert isinstance(root.source, Arbiter)
    assert root.source.registry is profile.sources


def test_empty_source_registry_weaves_empty_envelope() -> None:
    profile = ProfileDef(
        sources=SourceRegistry(sources={}),
        calculators=CalculatorRegistry(calculators={}),
        root_store=_root_store(),
        arbiter=ArbiterPolicy(),
    )
    root = Weaver(RecordingStoreFactory()).weave(profile)
    assert root.capability.parameters == {}


def test_nonempty_calculator_registry_not_implemented() -> None:
    calcs = CalculatorRegistry(
        calculators={
            WIND_SPEED: RegisteredCalculator(
                output=WIND_SPEED,
                inputs=frozenset({WIND_U, WIND_V}),
                manifest=CalculatorManifest(fn_id="wind_speed", fn=lambda *a: None),
            )
        }
    )
    profile = _profile(
        offerings=[OfferingDef(impl="fake", name="default", priority=0)],
        calculators=calcs,
    )
    with pytest.raises(NotImplementedError, match="Calculator"):
        Weaver(RecordingStoreFactory()).weave(profile)
