"""MCP surface adapter: protocol <-> canonical, the first surface.

Builds the FastMCP app and registers the one v1 tool, `get_forecast`. In this slice the tool is
*registered* but carries no forecast behaviour - translating the call into a canonical `Selection`,
driving the Gateway, and serializing the Coverage to compact JSON (by iterating the Coverage
interface) is wired from 001 onward.
"""

from __future__ import annotations

from fastmcp import FastMCP


def build_mcp_app() -> FastMCP:
    """Construct the MCP app with `get_forecast` registered (no forecast behaviour yet)."""
    mcp: FastMCP = FastMCP("meteoscape")

    @mcp.tool
    def get_forecast(
        latitude: float,
        longitude: float,
        parameters: list[str] | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, object]:
        """Hourly point forecast for a latitude/longitude.

        Optional `parameters` selects a subset of the core-5 (default all); `start`/`end` bound the
        window (default a configured horizon). Returns a normalized, provenance-stamped Timeline.
        """
        raise NotImplementedError

    return mcp
