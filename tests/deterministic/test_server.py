"""Composition root (`compose`) and MCP registration — mirrors `server.py`."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from fakes import STOPPED, TWC_PRIMARY_OFFERINGS, fake_catalog, pinned_settings
from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import StoppedClock
from meteoscape.config import (
    ArbiterPolicy,
    CalculatorDef,
    OfferingDef,
    ProfileConfig,
    Settings,
    StoreSpec,
)
from meteoscape.identity import SourceKey
from meteoscape.nodes.calculators import builtin as calculators
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.nodes.composition import CompositionError, SourceBinder
from meteoscape.nodes.providers import builtin as providers
from meteoscape.parameters import AIR_TEMPERATURE, WIND_SPEED
from meteoscape.server import CALCULATORS, OFFERINGS, compose


def _public_profile(settings: Settings) -> ProfileConfig:
    return ProfileConfig(OFFERINGS, CALCULATORS, settings.root_store(), ArbiterPolicy())


def test_compose_advertises_enabled_offerings() -> None:
    profile = ProfileConfig(
        offerings=(OfferingDef(impl="fake", name="default", priority=0),),
        calculators=(),
        root_store=StoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14)),
        arbiter=ArbiterPolicy(),
    )
    gateway = compose(profile, fake_catalog(), {}, {}, STOPPED)
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters


def test_compose_rejects_unproducible_calculator_input() -> None:
    """`validate_calculators` is `weave`'s first step, so an operator's misconfigured profile fails
    `compose()` with a `CompositionError` naming the input and calculator — before any Store exists."""
    profile = ProfileConfig(
        offerings=(
            OfferingDef(impl="fake", name="default", priority=0),
        ),  # serves temperature only
        calculators=(CalculatorDef("wind_uv"),),
        root_store=StoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14)),
        arbiter=ArbiterPolicy(),
    )
    with pytest.raises(CompositionError, match=r"wind_u") as exc:
        compose(profile, fake_catalog(), calculators.CATALOG, {}, STOPPED)
    assert "wind_uv" in str(exc.value)


def test_public_profile_boots_keyless_on_open_meteo() -> None:
    settings = pinned_settings()
    gateway = compose(
        _public_profile(settings),
        providers.CATALOG,
        calculators.CATALOG,
        {},
        STOPPED,
    )
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters
    assert WIND_SPEED in gateway.best_view.capability.parameters
    assert "open-meteo" in providers.CATALOG
    assert "twc" in providers.CATALOG
    assert "wind_uv" in calculators.CATALOG
    registry = SourceBinder(providers.CATALOG).build(
        OFFERINGS,
        {},
        STOPPED,
        StaticParameterTable.core(),
    )
    assert set(registry.sources) == {SourceKey(provider="open-meteo", dataset="best_match")}


def test_public_compose_and_forecast_hourly_registered() -> None:
    settings = pinned_settings()
    clock = StoppedClock(datetime(2026, 7, 11, tzinfo=UTC))
    gateway = compose(
        _public_profile(settings),
        providers.CATALOG,
        calculators.CATALOG,
        {},
        clock,
    )
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters

    app = build_mcp_app(gateway, clock)
    tool = asyncio.run(app.get_tool("forecast_hourly"))
    assert tool is not None
    assert tool.name == "forecast_hourly"
    assert "air_temperature" in (tool.description or "")


def test_embedder_profile_composes_twc_as_primary() -> None:
    settings = pinned_settings()
    profile = ProfileConfig(
        TWC_PRIMARY_OFFERINGS,
        CALCULATORS,
        settings.root_store(),
        ArbiterPolicy(),
    )
    secrets = {"twc": "secret"}
    gateway = compose(
        profile,
        providers.CATALOG,
        calculators.CATALOG,
        secrets,
        STOPPED,
    )
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters
    registry = SourceBinder(providers.CATALOG).build(
        TWC_PRIMARY_OFFERINGS,
        secrets,
        STOPPED,
        StaticParameterTable.core(),
    )
    twc = SourceKey(provider="twc", dataset="hourly_10day")
    om = SourceKey(provider="open-meteo", dataset="best_match")
    assert registry.sources[twc].priority == 0
    assert registry.sources[om].priority == 1
    assert AIR_TEMPERATURE in registry.sources[twc].provider.capability.parameters
    assert AIR_TEMPERATURE in registry.sources[om].provider.capability.parameters


def test_embedder_profile_without_the_key_refuses() -> None:
    with pytest.raises(CompositionError, match="METEOSCAPE_TWC_API_KEY") as exc:
        SourceBinder(providers.CATALOG).build(
            TWC_PRIMARY_OFFERINGS,
            {},
            STOPPED,
            StaticParameterTable.core(),
        )
    message = str(exc.value)
    assert "twc" in message
    assert "api_key" in message


def test_leftover_env_var_is_inert() -> None:
    """Env carries secrets and scalars only — a stale var reaches no `build` (0123 align)."""
    settings = pinned_settings()
    gateway = compose(
        _public_profile(settings),
        providers.CATALOG,
        calculators.CATALOG,
        {"open_meteo_enabled": "true", "open_meteo_cadence_hours": "3"},
        STOPPED,
    )
    assert gateway is not None


def test_leftover_twc_key_is_inert_on_the_public_profile() -> None:
    settings = pinned_settings()
    gateway = compose(
        _public_profile(settings),
        providers.CATALOG,
        calculators.CATALOG,
        {"twc": "secret"},
        STOPPED,
    )
    registry = SourceBinder(providers.CATALOG).build(
        OFFERINGS,
        {"twc": "secret"},
        STOPPED,
        StaticParameterTable.core(),
    )
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters
    assert set(registry.sources) == {SourceKey(provider="open-meteo", dataset="best_match")}


def test_unknown_twc_offering_fails_at_boot() -> None:
    with pytest.raises(CompositionError, match="nope"):
        SourceBinder(providers.CATALOG).build(
            [OfferingDef(impl="twc", name="nope", priority=0)],
            {"twc": "secret"},
            STOPPED,
            StaticParameterTable.core(),
        )
