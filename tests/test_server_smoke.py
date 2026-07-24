"""Smoke test: the MCP server constructs and registers `forecast_hourly`."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from meteoscape.api.gateway import Gateway
from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import StoppedClock
from meteoscape.manifold.capability import UnionCapability
from meteoscape.manifold.core import Manifold, Selection


class _EmptyView:
    async def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError

    @property
    def capability(self):
        return UnionCapability(members={}, domains={})


def test_forecast_hourly_is_registered() -> None:
    app = build_mcp_app(
        Gateway(_EmptyView()),
        StoppedClock(datetime(2026, 7, 11, tzinfo=UTC)),
        timedelta(days=7),
    )
    tool = asyncio.run(app.get_tool("forecast_hourly"))
    assert tool is not None
    assert tool.name == "forecast_hourly"
