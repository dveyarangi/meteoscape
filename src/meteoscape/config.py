"""Typed settings - pure data, injected at construction.

Provider enablement + secrets, the policy config (priority ordering), and cache/grid tuning. Secrets
are injected, never read from globals downstream. `nodes/` receive plain values from `server.py`,
never this type. The defaults encode v1's positions (Open-Meteo primary, TWC fallback).
"""

from __future__ import annotations

from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="METEOSCAPE_", env_file=".env", extra="ignore")

    enabled_providers: tuple[str, ...] = ("open-meteo",)
    """Providers the Registry instantiates. A missing optional secret degrades gracefully."""

    twc_api_key: str | None = None
    """The Weather Company key (optional). Absent => serve on Open-Meteo alone."""

    arbiter_priority: tuple[str, ...] = ("open-meteo", "twc")
    """Per-parameter candidate ordering - the implicit quality policy (select, never combine)."""

    store_spatial_step: float = 0.1
    """Best-view store grid step in degrees (a configured guess; the cache lattice / fidelity floor)."""

    retention_interval: timedelta = timedelta(days=14)
    """Time-based eviction bound (memory housekeeping; freshness is `expiration`, not this)."""

    default_horizon: timedelta = timedelta(days=7)
    """Forward horizon applied only when the caller omits `end`."""
