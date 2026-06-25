"""Composition root - the thin entrypoint.

Initializes observability and stands up the MCP surface. The full DAG wiring (config -> Registry ->
Weaver -> Gateway -> surface) lands in 001; `server.py` holds no construction logic of its own.
"""

from __future__ import annotations

from .api.mcp_app import build_mcp_app
from .observability import init_observability


def main() -> None:
    init_observability()
    app = build_mcp_app()
    app.run()
