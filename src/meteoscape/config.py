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
class StoreSpec:
    """Knobs for a Store that needs a configured guess — profile root or non-Countable Source."""

    spatial_step: float
    retention_interval: timedelta


@dataclass(frozen=True)
class OfferingDef:
    """Profile enablement ticket for one catalogue offering.

    Points at `ProviderManifest` via `impl` (+ optional `name`); no raw `SourceKey`, no geometry.
    `name=None` selects the expand path. Optional `store` whole-spec-replaces the catalogue
    `StoreSpec` for non-Countable Sources.
    """

    impl: str
    priority: int
    name: str | None = None
    secret_ref: str | None = None
    settings: Mapping[str, object] = field(default_factory=dict)
    store: StoreSpec | None = None


@dataclass(frozen=True)
class CalculatorDef:
    """Profile enablement of one calculator — peer of `OfferingDef`.

    Points at a `CalculatorManifest` via `fn_id`; `outputs` is the co-produced output group.
    `name=None` binder-defaults to `"default"`. Bound via `CalculatorBinder` before weave.
    """

    outputs: frozenset[ParameterId]
    inputs: frozenset[ParameterId]
    fn_id: str
    priority: int
    name: str | None = None
    stored: bool = False


@dataclass(frozen=True)
class ArbiterPolicy:
    """Arbiter reconciler mode(s) for a profile; v1 ships only `priority`."""

    default_reconciler: str = "priority"


@dataclass(frozen=True)
class ProfileConfig:
    """Operator-side, per-profile enablement — offerings, calculators, root store, arbiter."""

    offerings: tuple[OfferingDef, ...]
    calculators: tuple[CalculatorDef, ...]
    root_store: StoreSpec
    arbiter: ArbiterPolicy


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="METEOSCAPE_", env_file=".env", extra="ignore")

    open_meteo_enabled: bool = True
    """Include the Open-Meteo producer. Keyless; off disables the primary source."""

    twc_api_key: str | None = None
    """The Weather Company key (optional). Absent => serve on Open-Meteo alone."""

    store_spatial_step: float = 0.0001
    """Best-view store grid step in degrees — the cache lattice / fidelity floor. v1 default ~11 m:
    effectively a per-point cache (repeat requests hit; distinct points don't share), trading spatial
    cache sharing for near-exact values under the nearest-neighbor read-back."""

    retention_interval: timedelta = timedelta(days=14)
    """Time-based eviction bound (memory housekeeping; freshness is `expiration`, not this)."""

    default_horizon: timedelta = timedelta(days=7)
    """Forward horizon applied only when the caller omits `end`."""

    def offerings(self) -> tuple[OfferingDef, ...]:
        """Enabled producer tickets — explicit offering names (no catalogue import)."""
        defs: list[OfferingDef] = []
        if self.open_meteo_enabled:
            defs.append(OfferingDef(impl="open-meteo", name="best_match", priority=0))
        if self.twc_api_key is not None:
            defs.append(
                OfferingDef(
                    impl="twc",
                    name="default",
                    priority=1,
                    secret_ref="twc_api_key",
                )
            )
        return tuple(defs)

    def calculators(self) -> tuple[CalculatorDef, ...]:
        """Derived-parameter recipes enabled for the default profile."""
        return (
            CalculatorDef(
                outputs=frozenset({WIND_SPEED, WIND_DIRECTION}),
                inputs=frozenset({WIND_U, WIND_V}),
                fn_id="wind_uv",
                priority=0,
            ),
        )

    def profile(self) -> ProfileConfig:
        """v1 single best-view profile projected from env scalars."""
        return ProfileConfig(
            offerings=self.offerings(),
            calculators=self.calculators(),
            root_store=StoreSpec(
                spatial_step=self.store_spatial_step,
                retention_interval=self.retention_interval,
            ),
            arbiter=ArbiterPolicy(),
        )

    def secrets(self) -> Mapping[str, str]:
        """Injected secret map keyed by `OfferingDef.secret_ref` names."""
        out: dict[str, str] = {}
        if self.twc_api_key is not None:
            out["twc_api_key"] = self.twc_api_key
        return out
