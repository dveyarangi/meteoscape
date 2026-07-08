"""Smoke test: the MCP server constructs and registers `get_forecast`.

Structural only - it does not invoke the tool (there is no forecast behaviour in this slice).
"""

import asyncio

from meteoscape.api.mcp_app import build_mcp_app


def test_get_forecast_is_registered() -> None:
    app = build_mcp_app()
    tool = asyncio.run(app.get_tool("get_forecast"))
    assert tool is not None
    assert tool.name == "get_forecast"
