"""Typed settings - pure data, injected at construction.

`ProfileConfig` (operator enablement per profile), secrets, and cache/grid tuning. Secrets are
injected, never read from globals downstream. `nodes/` receive plain values from `server.py`, never
this type. The defaults encode v1's positions (Open-Meteo primary, TWC fallback).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict

from .parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V, ParameterId


@dataclass(frozen=True)
class SourceDef:
    """Profile enablement ticket for one catalogue offering.

    Points at `ProviderManifest` via `impl` (+ optional `offering`); no raw `SourceKey`, no geometry.
    `offering=None` selects the expand path. Naming → concern #22 (`OfferingDef`).
    """

    impl: str
    priority: int
    offering: str | None = None
    secret_ref: str | None = None
    settings: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DerivationSpec:
    """Profile recipe for one derived parameter — bound via `DerivationBinder` before weave."""

    output: ParameterId
    inputs: frozenset[ParameterId]
    fn_id: str
    stored: bool = False


@dataclass(frozen=True)
class RootStoreSpec:
    """Profile-root Reservoir store knobs (lattice guess + retention) — separate from Source lattices."""

    spatial_step: float
    retention_interval: timedelta


@dataclass(frozen=True)
class ArbiterPolicy:
    """Arbiter reconciler mode(s) for a profile; v1 ships only `priority`."""

    default_reconciler: str = "priority"


@dataclass(frozen=True)
class ProfileConfig:
    """Operator-side, per-profile enablement — sources, derivations, root store, arbiter."""

    sources: tuple[SourceDef, ...]
    derivations: tuple[DerivationSpec, ...]
    root_store: RootStoreSpec
    arbiter: ArbiterPolicy


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
        """Enabled producer tickets — explicit offering names (no catalogue import)."""
        defs: list[SourceDef] = []
        if self.open_meteo_enabled:
            defs.append(SourceDef(impl="open-meteo", offering="best_match", priority=0))
        if self.twc_api_key is not None:
            defs.append(
                SourceDef(
                    impl="twc",
                    offering="default",
                    priority=1,
                    secret_ref="twc_api_key",
                )
            )
        return tuple(defs)

    def derivations(self) -> tuple[DerivationSpec, ...]:
        """v1 derived wind views over canonical u/v."""
        uv = frozenset({WIND_U, WIND_V})
        return (
            DerivationSpec(output=WIND_SPEED, inputs=uv, fn_id="wind_speed"),
            DerivationSpec(output=WIND_DIRECTION, inputs=uv, fn_id="wind_direction"),
        )

    def profile(self) -> ProfileConfig:
        """v1 single best-view profile projected from env scalars."""
        return ProfileConfig(
            sources=self.sources(),
            derivations=self.derivations(),
            root_store=RootStoreSpec(
                spatial_step=self.store_spatial_step,
                retention_interval=self.retention_interval,
            ),
            arbiter=ArbiterPolicy(),
        )

    def secrets(self) -> Mapping[str, str]:
        """Injected secret map keyed by `SourceDef.secret_ref` names."""
        out: dict[str, str] = {}
        if self.twc_api_key is not None:
            out["twc_api_key"] = self.twc_api_key
        return out
