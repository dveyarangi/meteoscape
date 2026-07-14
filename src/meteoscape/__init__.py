"""Meteoscape - a manifold-based weather Coverage-resolution engine, served over MCP."""

from .identity import SourceKey
from .server import main

__all__ = ["SourceKey", "main"]
