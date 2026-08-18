"""Composition root (`compose`) and MCP registration — mirrors `server.py`."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from fakes import STOPPED, fake_catalog, pinned_settings
from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import StoppedClock
from meteoscape.config import (
    ArbiterPolicy,
    CalculatorDef,
    OfferingDef,
    ProfileConfig,
    StoreSpec,
)
from meteoscape.identity import SourceKey
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.nodes.composition import CompositionError, SourceBinder
from meteoscape.parameters import AIR_TEMPERATURE, WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V
from meteoscape.server import CALCULATOR_CATALOG, PROVIDER_CATALOG, compose


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
        calculators=(
            CalculatorDef(
                outputs=frozenset({WIND_SPEED, WIND_DIRECTION}),
                inputs=frozenset({WIND_U, WIND_V}),
                fn_id="wind_uv",
                priority=0,
            ),
        ),
        root_store=StoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14)),
        arbiter=ArbiterPolicy(),
    )
    with pytest.raises(CompositionError, match=r"wind_u") as exc:
        compose(profile, fake_catalog(), CALCULATOR_CATALOG, {}, STOPPED)
    assert "wind_uv" in str(exc.value)


def test_default_settings_compose_open_meteo() -> None:
    settings = pinned_settings()
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        STOPPED,
    )
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters
    assert WIND_SPEED in gateway.best_view.capability.parameters
    assert "open-meteo" in PROVIDER_CATALOG
    assert "twc" in PROVIDER_CATALOG
    assert "wind_uv" in CALCULATOR_CATALOG


def test_default_compose_and_forecast_hourly_registered() -> None:
    settings = pinned_settings()
    clock = StoppedClock(datetime(2026, 7, 11, tzinfo=UTC))
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        clock,
    )
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters

    app = build_mcp_app(gateway, clock)
    tool = asyncio.run(app.get_tool("forecast_hourly"))
    assert tool is not None
    assert tool.name == "forecast_hourly"
    assert "air_temperature" in (tool.description or "")


def test_key_present_composes_twc_as_primary() -> None:
    settings = pinned_settings(twc_api_key="secret")
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        STOPPED,
    )
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters
    registry = SourceBinder(PROVIDER_CATALOG).build(
        settings.offerings(),
        settings.secrets(),
        STOPPED,
        StaticParameterTable.core(),
    )
    twc = SourceKey(provider="twc", dataset="hourly_10day")
    om = SourceKey(provider="open-meteo", dataset="best_match")
    assert registry.sources[twc].priority == 0
    assert registry.sources[om].priority == 1
    assert AIR_TEMPERATURE in registry.sources[twc].provider.capability.parameters
    assert AIR_TEMPERATURE in registry.sources[om].provider.capability.parameters


def test_unknown_twc_offering_fails_at_boot() -> None:
    with pytest.raises(CompositionError, match="nope"):
        SourceBinder(PROVIDER_CATALOG).build(
            [OfferingDef(impl="twc", name="nope", priority=0, secret_ref="twc_api_key")],
            {"twc_api_key": "secret"},
            STOPPED,
            StaticParameterTable.core(),
        )
