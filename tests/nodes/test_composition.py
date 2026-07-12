"""SourceBinder / CalculatorBinder — build-time registry construction."""

from __future__ import annotations

from datetime import timedelta

import pytest

from fakes import SAMPLE_STORE, STOPPED, core_parameters, fake_catalog
from meteoscape.config import CalculatorSpec, OfferingDef, StoreSpec
from meteoscape.identity import SourceKey
from meteoscape.manifold.core import Countable
from meteoscape.nodes.catalog.calculators import CalculatorManifest
from meteoscape.nodes.catalog.providers import OfferingSpec, SecretSlot
from meteoscape.nodes.composition import CalculatorBinder, CompositionError, SourceBinder
from meteoscape.parameters import AIR_TEMPERATURE, WIND_SPEED, WIND_U, WIND_V


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


def test_calculator_binder_empty_and_unknown() -> None:
    empty = CalculatorBinder({}).build(())
    assert empty.calculators == {}

    catalog = {
        "wind_speed": CalculatorManifest(fn_id="wind_speed", fn=lambda *a: None),
    }
    bound = CalculatorBinder(catalog).build(
        [
            CalculatorSpec(
                output=WIND_SPEED,
                inputs=frozenset({WIND_U, WIND_V}),
                fn_id="wind_speed",
            )
        ]
    )
    assert set(bound.calculators) == {WIND_SPEED}
    assert bound.calculators[WIND_SPEED].manifest.fn_id == "wind_speed"

    with pytest.raises(CompositionError, match="fn_id"):
        CalculatorBinder(catalog).build(
            [
                CalculatorSpec(
                    output=WIND_SPEED,
                    inputs=frozenset({WIND_U, WIND_V}),
                    fn_id="missing",
                )
            ]
        )
