"""MCP surface adapter: protocol <-> canonical, the first surface.

Builds the FastMCP app and registers the one v1 tool, `get_forecast`. The adapter's job is to
translate a call into a canonical `Selection`, drive the Gateway, and serialize the returned Coverage.
"""

from __future__ import annotations

from fastmcp import FastMCP


def build_mcp_app() -> FastMCP:
    """Construct the MCP app with `get_forecast` registered."""
    mcp: FastMCP = FastMCP("meteoscape")

    @mcp.tool
    async def get_forecast(
        latitude: float,
        longitude: float,
        parameters: list[str] | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, object]:
        """Hourly point forecast for a latitude/longitude.

        Optional `parameters` selects a subset of the 5 product params (default all); `start`/`end` bound the
        window (default a configured horizon). Returns a normalized, provenance-stamped Timeline.
        """
        raise NotImplementedError

    return mcp
