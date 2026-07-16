"""Composition root (`compose`) and MCP registration — mirrors `server.py`."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fakes import STOPPED, RecordingStoreFactory, fake_catalog
from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import StoppedClock
from meteoscape.config import ArbiterPolicy, OfferingDef, ProfileConfig, Settings, StoreSpec
from meteoscape.nodes.store import StoreFactory
from meteoscape.parameters import AIR_TEMPERATURE, WIND_SPEED
from meteoscape.server import CALCULATOR_CATALOG, PROVIDER_CATALOG, compose


def test_compose_advertises_enabled_offerings() -> None:
    profile = ProfileConfig(
        offerings=(OfferingDef(impl="fake", name="default", priority=0),),
        calculators=(),
        root_store=StoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14)),
        arbiter=ArbiterPolicy(),
    )
    gateway = compose(profile, fake_catalog(), {}, {}, STOPPED, RecordingStoreFactory())
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters


def test_default_settings_compose_open_meteo() -> None:
    settings = Settings()
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        STOPPED,
        StoreFactory(),
    )
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters
    assert WIND_SPEED in gateway.best_view.capability.parameters
    assert "open-meteo" in PROVIDER_CATALOG
    assert "wind_uv" in CALCULATOR_CATALOG


def test_default_compose_and_forecast_hourly_registered() -> None:
    settings = Settings()
    clock = StoppedClock(datetime(2026, 7, 11, tzinfo=UTC))
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        clock,
        StoreFactory(),
    )
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters

    app = build_mcp_app(gateway, clock, settings.default_horizon)
    tool = asyncio.run(app.get_tool("forecast_hourly"))
    assert tool is not None
    assert tool.name == "forecast_hourly"
    assert "air_temperature" in (tool.description or "")
