"""Composition root (`compose`) and MCP smoke — mirrors `server.py`."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fakes import STOPPED, RecordingStoreFactory, fake_catalog
from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import StoppedClock
from meteoscape.config import ArbiterPolicy, OfferingDef, ProfileConfig, RootStoreSpec, Settings
from meteoscape.nodes.store import StoreFactory
from meteoscape.parameters import AIR_TEMPERATURE
from meteoscape.server import PROVIDER_CATALOG, compose


def test_compose_advertises_enabled_offerings() -> None:
    profile = ProfileConfig(
        offerings=(OfferingDef(impl="fake", name="default", priority=0),),
        calculators=(),
        root_store=RootStoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14)),
        arbiter=ArbiterPolicy(),
    )
    gateway = compose(profile, fake_catalog(), {}, STOPPED, RecordingStoreFactory())
    assert AIR_TEMPERATURE in gateway.best_view.capability.parameters


def test_default_settings_compose_empty_weave() -> None:
    settings = Settings()
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        settings.secrets(),
        STOPPED,
        StoreFactory(),
    )
    assert gateway.best_view.capability.parameters == {}


def test_default_compose_and_get_forecast_registered() -> None:
    settings = Settings()
    gateway = compose(
        settings.profile(),
        PROVIDER_CATALOG,
        settings.secrets(),
        StoppedClock(datetime(2026, 7, 11, tzinfo=UTC)),
        StoreFactory(),
    )
    assert gateway.best_view.capability.parameters == {}

    app = build_mcp_app()
    tool = asyncio.run(app.get_tool("get_forecast"))
    assert tool is not None
    assert tool.name == "get_forecast"
