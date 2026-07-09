"""Typed settings - pure data, injected at construction.

`SourceDef` recipes (enabled producers), secrets, and cache/grid tuning. Secrets are injected, never
read from globals downstream. `nodes/` receive plain values from `server.py`, never this type. The
defaults encode v1's positions (Open-Meteo primary, TWC fallback).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict

from .identity import SourceKey


@dataclass(frozen=True)
class SourceDef:
    """Config recipe for one configured producer - a `SourceKey` plus build knobs.

    `dataset` is fixed here at construction, so distinct offerings are distinct `SourceDef`s. The
    Registry builds one instance per recipe; `priority` is per-`SourceDef` policy (equal ranks are
    score-tie-broken peers). See ADR-0004 / architecture ("Config, Registry, Weaver").
    """

    key: SourceKey  # (provider, dataset) e.g. SourceKey("open-meteo", "best_match")
    impl: str  # Registry catalog id -> Provider class
    priority: int  # per-SourceDef rank; equal ranks are score-tie-broken peers
    secret_ref: str | None = None  # names a secret in the injected secret map; None = keyless


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="METEOSCAPE_", env_file=".env", extra="ignore")

    open_meteo_enabled: bool = True
    """Include the Open-Meteo producer. Keyless; off disables the primary source."""

    twc_api_key: str | None = None
    """The Weather Company key (optional). Absent => serve on Open-Meteo alone."""

    store_spatial_step: float = 0.1
    """Best-view store grid step in degrees (a configured guess; the cache lattice / fidelity floor)."""

    retention_interval: timedelta = timedelta(days=14)
    """Time-based eviction bound (memory housekeeping; freshness is `expiration`, not this)."""

    default_horizon: timedelta = timedelta(days=7)
    """Forward horizon applied only when the caller omits `end`."""

    def sources(self) -> tuple[SourceDef, ...]:
        """Enabled producer recipes - one `SourceDef` per configured offering."""
        defs: list[SourceDef] = []
        if self.open_meteo_enabled:
            defs.append(
                SourceDef(
                    key=SourceKey("open-meteo", "best_match"),
                    impl="open-meteo",
                    priority=0,
                )
            )
        if self.twc_api_key is not None:
            defs.append(
                SourceDef(
                    key=SourceKey("twc", "default"),
                    impl="twc",
                    priority=1,
                    secret_ref="twc_api_key",
                )
            )
        return tuple(defs)

    def secrets(self) -> Mapping[str, str]:
        """Injected secret map keyed by `SourceDef.secret_ref` names."""
        out: dict[str, str] = {}
        if self.twc_api_key is not None:
            out["twc_api_key"] = self.twc_api_key
        return out
