"""Weaver — allocate stores, wrap Producers, wire Arbiter (+ calculator memoization)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from fakes import (
    SAMPLE_STORE,
    STOPPED,
    RecordingProvider,
    RecordingStoreFactory,
    core_parameters,
    coverage_record,
    fake_catalog,
    sample_lattice,
)
from meteoscape.config import ArbiterPolicy, OfferingDef, StoreSpec
from meteoscape.identity import CalculatorKey, SourceKey
from meteoscape.manifold.core import Selection
from meteoscape.nodes.arbiter import Arbiter
from meteoscape.nodes.calculator import Calculator
from meteoscape.nodes.calculators.wind import wind_from_uv
from meteoscape.nodes.catalog.calculators import CalculatorManifest
from meteoscape.nodes.catalog.providers import OfferingSpec
from meteoscape.nodes.composition import (
    CalculatorRegistry,
    CompositionError,
    ProfileDef,
    RegisteredCalculator,
    RegisteredSource,
    SourceBinder,
    SourceRegistry,
)
from meteoscape.nodes.reservoir import Reservoir
from meteoscape.nodes.weaver import Weaver
from meteoscape.parameters import (
    AIR_TEMPERATURE,
    WIND_DIRECTION,
    WIND_SPEED,
    WIND_U,
    WIND_V,
)


def _root_store() -> StoreSpec:
    return StoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14))


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


def _wind_registry(*, stored: bool = False) -> CalculatorRegistry:
    parameters = core_parameters()
    key = CalculatorKey(method="wind_uv", name="default")
    return CalculatorRegistry(
        calculators={
            key: RegisteredCalculator(
                key=key,
                outputs={
                    WIND_SPEED: parameters.get(WIND_SPEED),
                    WIND_DIRECTION: parameters.get(WIND_DIRECTION),
                },
                inputs=frozenset({WIND_U, WIND_V}),
                manifest=CalculatorManifest(fn_id="wind_uv", fn=wind_from_uv),
                priority=0,
                stored=stored,
            )
        }
    )


def _canonical_with_wind_catalog():
    return fake_catalog(
        offerings={
            "default": OfferingSpec(
                name="default",
                parameters=frozenset({AIR_TEMPERATURE, WIND_U, WIND_V}),
                store=SAMPLE_STORE,
            )
        }
    )


def test_single_source_weaves_capability_and_stores() -> None:
    stores = RecordingStoreFactory()
    profile = _profile(offerings=[OfferingDef(impl="fake", name="default", priority=0)])
    root = Weaver(stores).weave(profile)

    assert isinstance(root, Reservoir)
    assert AIR_TEMPERATURE in root.capability.parameters
    assert len(stores.calls) == 2
    source_store = next(iter(profile.sources.sources.values())).store
    assert stores.calls[0] is source_store
    assert stores.calls[1] is profile.root_store
    assert isinstance(root.source, Arbiter)
    assert len(root.source.producers) == 1
    assert root.source.producers[0].key in profile.sources.sources


def test_materialized_source_weaves_storeless() -> None:
    """A materialized source wires as a bare `Producer` — no `Reservoir`, no store allocated for it."""
    stores = RecordingStoreFactory()
    profile = _profile(
        offerings=[OfferingDef(impl="fake", name="default", priority=0)],
        catalog=fake_catalog(materialized=True),
    )
    root = Weaver(stores).weave(profile)
    assert isinstance(root, Reservoir)
    assert isinstance(root.source, Arbiter)

    entry = next(iter(profile.sources.sources.values()))
    producer = next(p for p in root.source.producers if p.key in profile.sources.sources)
    assert producer.node is entry.provider  # the provider itself, unwrapped
    assert stores.calls == [profile.root_store]  # only the best-view store; none for the source
    assert AIR_TEMPERATURE in root.capability.parameters


@pytest.mark.asyncio
async def test_materialized_source_serves_through_arbiter() -> None:
    """The Arbiter projects the bare materialized leaf and its answer is served as-is.

    On-grid on purpose: a storeless leaf does not homogenize (concern #37), so the Selection rides
    the leaf's own declared domain. `RecordingProvider` derives its capability from the coverage —
    the materialized shape.
    """
    domain = sample_lattice(count=1)
    coverage = coverage_record(AIR_TEMPERATURE, domain=domain, value=21.5)
    leaf = RecordingProvider(source_key=SourceKey("fake", "default"), coverage=coverage)
    profile = ProfileDef(
        sources=SourceRegistry(
            sources={leaf.source_key: RegisteredSource(provider=leaf, priority=0, store=None)}
        ),
        calculators=CalculatorRegistry(calculators={}),
        root_store=_root_store(),
        arbiter=ArbiterPolicy(),
    )
    root = Weaver(RecordingStoreFactory()).weave(profile)

    selection = Selection(domain=domain, parameters=frozenset({AIR_TEMPERATURE}))
    result = await root.project(selection)

    assert result is coverage  # the leaf's own answer, straight through the Arbiter
    assert len(leaf.calls) == 1
    assert leaf.calls[0].domain is domain


def test_empty_source_registry_weaves_empty_envelope() -> None:
    profile = ProfileDef(
        sources=SourceRegistry(sources={}),
        calculators=CalculatorRegistry(calculators={}),
        root_store=_root_store(),
        arbiter=ArbiterPolicy(),
    )
    root = Weaver(RecordingStoreFactory()).weave(profile)
    assert root.capability.parameters == {}


def test_wind_calculator_memoized_as_single_producer() -> None:
    profile = _profile(
        offerings=[OfferingDef(impl="fake", name="default", priority=0)],
        catalog=_canonical_with_wind_catalog(),
        calculators=_wind_registry(),
    )
    root = Weaver(RecordingStoreFactory()).weave(profile)
    assert isinstance(root, Reservoir)
    assert isinstance(root.source, Arbiter)
    calc_keys = [p.key for p in root.source.producers if isinstance(p.key, CalculatorKey)]
    assert calc_keys == [CalculatorKey(method="wind_uv", name="default")]
    assert WIND_SPEED in root.capability.parameters
    assert WIND_DIRECTION in root.capability.parameters
    assert AIR_TEMPERATURE in root.capability.parameters
    calc = next(p for p in root.source.producers if isinstance(p.key, CalculatorKey))
    assert isinstance(calc.node, Calculator)
    assert set(calc.node.outputs) == {WIND_SPEED, WIND_DIRECTION}


def test_scoped_arbiter_admits_only_input_producers() -> None:
    profile = _profile(
        offerings=[OfferingDef(impl="fake", name="default", priority=0)],
        catalog=_canonical_with_wind_catalog(),
        calculators=_wind_registry(),
    )
    root = Weaver(RecordingStoreFactory()).weave(profile)
    assert isinstance(root, Reservoir)
    assert isinstance(root.source, Arbiter)
    calc = next(p for p in root.source.producers if isinstance(p.key, CalculatorKey))
    assert isinstance(calc.node, Calculator)
    scoped = calc.node.resolver
    assert isinstance(scoped, Arbiter)
    assert all(isinstance(p.key, SourceKey) for p in scoped.producers)
    served = {pid for p in scoped.producers for pid in p.node.capability.parameters}
    assert WIND_U in served and WIND_V in served
    assert WIND_SPEED not in served and WIND_DIRECTION not in served
    # Scope (defect 1): the resolver declares exactly the Calculator's inputs — not AIR_TEMPERATURE,
    # which its whole-producer members also serve — and reach answers in-scope, raises out.
    assert set(scoped.capability.parameters) == {WIND_U, WIND_V}
    scoped.capability.reach(WIND_U)
    scoped.capability.reach(WIND_V)
    with pytest.raises(KeyError):
        scoped.capability.reach(AIR_TEMPERATURE)


def test_calculator_cycle_raises() -> None:
    parameters = core_parameters()
    a = CalculatorKey(method="a", name="default")
    b = CalculatorKey(method="b", name="default")
    calcs = CalculatorRegistry(
        calculators={
            a: RegisteredCalculator(
                key=a,
                outputs={WIND_SPEED: parameters.get(WIND_SPEED)},
                inputs=frozenset({WIND_DIRECTION}),
                manifest=CalculatorManifest(fn_id="a", fn=wind_from_uv),
                priority=0,
            ),
            b: RegisteredCalculator(
                key=b,
                outputs={WIND_DIRECTION: parameters.get(WIND_DIRECTION)},
                inputs=frozenset({WIND_SPEED}),
                manifest=CalculatorManifest(fn_id="b", fn=wind_from_uv),
                priority=0,
            ),
        }
    )
    profile = _profile(
        offerings=[OfferingDef(impl="fake", name="default", priority=0)],
        calculators=calcs,
    )
    with pytest.raises(CompositionError, match="cycle"):
        Weaver(RecordingStoreFactory()).weave(profile)
