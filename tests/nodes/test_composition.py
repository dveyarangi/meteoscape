"""SourceBinder / CalculatorBinder — build-time registry construction."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import pytest

from fakes import SAMPLE_STORE, STOPPED, FakeProvider, core_parameters, fake_catalog
from meteoscape.config import ArbiterPolicy, CalculatorDef, OfferingDef, StoreSpec
from meteoscape.identity import CalculatorKey, SourceKey
from meteoscape.manifold.capability import FootprintCapability
from meteoscape.manifold.core import Countable, Coverage
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import (
    AxisName,
    ContinuousAxis,
    EnumerableDomain,
    FootprintDomain,
    Interval,
)
from meteoscape.nodes.calculators.wind import wind_from_uv
from meteoscape.nodes.catalog.calculators import CalculatorManifest
from meteoscape.nodes.catalog.providers import OfferingSpec, SecretSlot
from meteoscape.nodes.composition import (
    CalculatorBinder,
    CalculatorRegistry,
    CompositionError,
    ProfileDef,
    RegisteredCalculator,
    RegisteredSource,
    SourceBinder,
    SourceRegistry,
    validate_calculators,
)
from meteoscape.parameters import (
    AIR_TEMPERATURE,
    WIND_DIRECTION,
    WIND_SPEED,
    WIND_U,
    WIND_V,
    ParameterId,
)

_T0 = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)


def _never_called(
    coverage: Coverage,
) -> tuple[EnumerableDomain, Mapping[ParameterId, ParameterData]]:
    """A `CombineFn` the binder only stores — binding never invokes the kernel."""
    raise AssertionError("CalculatorBinder must not invoke the kernel")


def test_one_offering_binds_to_registry() -> None:
    catalog = fake_catalog()
    binder = SourceBinder(catalog)
    registry = binder.build(
        [OfferingDef(impl="fake", name="default", priority=0)],
        secrets={},
        clock=STOPPED,
        parameters=core_parameters(),
    )

    key = SourceKey(provider="fake", dataset="default")
    assert set(registry.sources) == {key}
    entry = registry.sources[key]
    assert entry.priority == 0
    assert entry.provider.source_key == key
    assert entry.store is SAMPLE_STORE


def test_countable_provider_drops_store() -> None:
    catalog = fake_catalog(countable=True)
    registry = SourceBinder(catalog).build(
        [OfferingDef(impl="fake", name="default", priority=0)],
        secrets={},
        clock=STOPPED,
        parameters=core_parameters(),
    )
    entry = next(iter(registry.sources.values()))
    assert isinstance(entry.provider, Countable)
    assert entry.store is None


def test_missing_store_raises() -> None:
    catalog = fake_catalog(
        offerings={
            "default": OfferingSpec(
                name="default",
                parameters=frozenset({AIR_TEMPERATURE}),
                store=None,
            )
        },
        countable=False,
    )
    with pytest.raises(CompositionError, match="store"):
        SourceBinder(catalog).build(
            [OfferingDef(impl="fake", name="default", priority=0)],
            secrets={},
            clock=STOPPED,
            parameters=core_parameters(),
        )


def test_offering_def_store_overrides_catalogue() -> None:
    override = StoreSpec(spatial_step=0.5, retention_interval=timedelta(days=7))
    registry = SourceBinder(fake_catalog()).build(
        [OfferingDef(impl="fake", name="default", priority=0, store=override)],
        secrets={},
        clock=STOPPED,
        parameters=core_parameters(),
    )
    entry = next(iter(registry.sources.values()))
    assert entry.store is override


def test_unknown_impl_raises() -> None:
    with pytest.raises(CompositionError, match="impl"):
        SourceBinder(fake_catalog()).build(
            [OfferingDef(impl="missing", name="default", priority=0)],
            secrets={},
            clock=STOPPED,
            parameters=core_parameters(),
        )


def test_unknown_offering_name_raises() -> None:
    with pytest.raises(CompositionError, match="offering"):
        SourceBinder(fake_catalog()).build(
            [OfferingDef(impl="fake", name="nope", priority=0)],
            secrets={},
            clock=STOPPED,
            parameters=core_parameters(),
        )


def test_secret_ref_reaches_build() -> None:
    built: list = []
    catalog = fake_catalog(secret=SecretSlot(name="api_key"), built=built)
    SourceBinder(catalog).build(
        [
            OfferingDef(
                impl="fake",
                name="default",
                priority=0,
                secret_ref="api_key",
                settings={"region": "eu"},
            )
        ],
        secrets={"api_key": "s3cret"},
        clock=STOPPED,
        parameters=core_parameters(),
    )
    assert built[0][2] == "s3cret"
    assert built[0][1] == {"region": "eu"}


def test_dangling_secret_ref_raises() -> None:
    with pytest.raises(CompositionError, match="secret_ref"):
        SourceBinder(fake_catalog()).build(
            [OfferingDef(impl="fake", name="default", priority=0, secret_ref="missing")],
            secrets={},
            clock=STOPPED,
            parameters=core_parameters(),
        )


def test_duplicate_source_key_raises() -> None:
    with pytest.raises(CompositionError, match="duplicate"):
        SourceBinder(fake_catalog()).build(
            [
                OfferingDef(impl="fake", name="default", priority=0),
                OfferingDef(impl="fake", name="default", priority=1),
            ],
            secrets={},
            clock=STOPPED,
            parameters=core_parameters(),
        )


def test_expand_name_none_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="expand"):
        SourceBinder(fake_catalog()).build(
            [OfferingDef(impl="fake", name=None, priority=0)],
            secrets={},
            clock=STOPPED,
            parameters=core_parameters(),
        )


def test_calculator_binder_empty() -> None:
    empty = CalculatorBinder({}).build((), core_parameters())
    assert empty.calculators == {}


def test_calculator_binder_resolves_key_outputs_and_priority() -> None:
    catalog = {
        "wind_uv": CalculatorManifest(fn_id="wind_uv", fn=_never_called),
    }
    parameters = core_parameters()
    bound = CalculatorBinder(catalog).build(
        [
            CalculatorDef(
                outputs=frozenset({WIND_SPEED, WIND_DIRECTION}),
                inputs=frozenset({WIND_U, WIND_V}),
                fn_id="wind_uv",
                priority=0,
            )
        ],
        parameters,
    )
    key = CalculatorKey(method="wind_uv", name="default")
    assert set(bound.calculators) == {key}
    entry = bound.calculators[key]
    assert entry.key == key
    assert entry.priority == 0
    assert entry.inputs == frozenset({WIND_U, WIND_V})
    assert entry.manifest.fn_id == "wind_uv"
    assert entry.outputs == {
        WIND_SPEED: parameters.get(WIND_SPEED),
        WIND_DIRECTION: parameters.get(WIND_DIRECTION),
    }


def test_calculator_binder_name_override() -> None:
    catalog = {
        "wind_uv": CalculatorManifest(fn_id="wind_uv", fn=_never_called),
    }
    bound = CalculatorBinder(catalog).build(
        [
            CalculatorDef(
                outputs=frozenset({WIND_SPEED, WIND_DIRECTION}),
                inputs=frozenset({WIND_U, WIND_V}),
                fn_id="wind_uv",
                priority=1,
                name="variant",
            )
        ],
        core_parameters(),
    )
    assert set(bound.calculators) == {CalculatorKey(method="wind_uv", name="variant")}


def test_calculator_binder_unknown_fn_id_raises() -> None:
    catalog = {
        "wind_uv": CalculatorManifest(fn_id="wind_uv", fn=_never_called),
    }
    with pytest.raises(CompositionError, match="fn_id"):
        CalculatorBinder(catalog).build(
            [
                CalculatorDef(
                    outputs=frozenset({WIND_SPEED}),
                    inputs=frozenset({WIND_U, WIND_V}),
                    fn_id="missing",
                    priority=0,
                )
            ],
            core_parameters(),
        )


def test_same_outputs_different_methods_are_distinct_keys() -> None:
    catalog = {
        "wind_uv": CalculatorManifest(fn_id="wind_uv", fn=_never_called),
        "wind_uv_alt": CalculatorManifest(fn_id="wind_uv_alt", fn=_never_called),
    }
    outputs = frozenset({WIND_SPEED, WIND_DIRECTION})
    inputs = frozenset({WIND_U, WIND_V})
    bound = CalculatorBinder(catalog).build(
        [
            CalculatorDef(outputs=outputs, inputs=inputs, fn_id="wind_uv", priority=0),
            CalculatorDef(outputs=outputs, inputs=inputs, fn_id="wind_uv_alt", priority=1),
        ],
        core_parameters(),
    )
    assert set(bound.calculators) == {
        CalculatorKey(method="wind_uv", name="default"),
        CalculatorKey(method="wind_uv_alt", name="default"),
    }


def test_duplicate_calculator_key_raises() -> None:
    catalog = {
        "wind_uv": CalculatorManifest(fn_id="wind_uv", fn=_never_called),
    }
    with pytest.raises(CompositionError, match="duplicate"):
        CalculatorBinder(catalog).build(
            [
                CalculatorDef(
                    outputs=frozenset({WIND_SPEED}),
                    inputs=frozenset({WIND_U, WIND_V}),
                    fn_id="wind_uv",
                    priority=0,
                ),
                CalculatorDef(
                    outputs=frozenset({WIND_DIRECTION}),
                    inputs=frozenset({WIND_U, WIND_V}),
                    fn_id="wind_uv",
                    priority=1,
                ),
            ],
            core_parameters(),
        )


# --- validate_calculators: inputs producible and the calculator graph acyclic ---


def _global() -> FootprintDomain:
    return FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(_T0, _T0 + timedelta(days=10))),
        }
    )


def _source(dataset: str, pids: frozenset[ParameterId]) -> tuple[SourceKey, RegisteredSource]:
    """A source serving `pids` — `validate_calculators` reads only which parameters are served."""
    key = SourceKey(provider="test", dataset=dataset)
    table = core_parameters()
    capability = FootprintCapability(footprints={pid: (table.get(pid), _global()) for pid in pids})
    return key, RegisteredSource(
        provider=FakeProvider(source_key=key, capability=capability),
        priority=0,
        store=SAMPLE_STORE,
    )


def _profile(
    sources: dict[SourceKey, RegisteredSource],
    calculators: CalculatorRegistry | None = None,
) -> ProfileDef:
    return ProfileDef(
        sources=SourceRegistry(sources=sources),
        calculators=calculators or CalculatorRegistry(calculators={}),
        root_store=StoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14)),
        arbiter=ArbiterPolicy(),
    )


def _wind_calculator() -> CalculatorRegistry:
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
            )
        }
    )


def _cycle_calculators() -> CalculatorRegistry:
    """a needs b's output and b needs a's — an unbuildable loop."""
    parameters = core_parameters()
    a = CalculatorKey(method="a", name="default")
    b = CalculatorKey(method="b", name="default")
    return CalculatorRegistry(
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


def test_validate_calculators_passes_when_inputs_served() -> None:
    key, source = _source("uv", frozenset({WIND_U, WIND_V}))
    validate_calculators(_profile({key: source}, _wind_calculator()))


def test_validate_calculators_raises_on_unserved_input() -> None:
    key, source = _source("temp-only", frozenset({AIR_TEMPERATURE}))
    with pytest.raises(CompositionError, match=r"wind_u") as exc:
        validate_calculators(_profile({key: source}, _wind_calculator()))
    assert "wind_uv" in str(exc.value)


def test_validate_calculators_raises_on_cycle() -> None:
    key, source = _source("temp", frozenset({AIR_TEMPERATURE}))
    with pytest.raises(CompositionError, match="cycle") as exc:
        validate_calculators(_profile({key: source}, _cycle_calculators()))
    # Names the cycle, not one arbitrary participant.
    assert str(exc.value).count("->") == 2
    assert "a:default" in str(exc.value) and "b:default" in str(exc.value)


def test_validate_calculators_catches_cycle_a_source_also_serves() -> None:
    """A source serving the looped parameters must not hide the cycle from the guard.

    The Weaver scopes each input Arbiter over *every* producer of that input, so the graph is
    unbuildable regardless of the source shadowing it.
    """
    key, source = _source("both", frozenset({WIND_SPEED, WIND_DIRECTION}))
    with pytest.raises(CompositionError, match="cycle"):
        validate_calculators(_profile({key: source}, _cycle_calculators()))
