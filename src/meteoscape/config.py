"""Profile declaration types, and the env spelling for secrets.

A profile — offerings, calculators, root store, arbiter policy — is *declared* at a composition
root, never projected from env: env carries secrets alone. `secret_env_name` / `secrets_from_env`
are the one home of that spelling. `nodes/` receive plain values from a root, never a config object.
See docs/architecture.md (Config, binders, Weaver) and ADR-0005.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from dotenv import dotenv_values

_ENV_PREFIX = "METEOSCAPE_"
_ENV_FILE = ".env"


@dataclass(frozen=True)
class StoreSpec:
    """Knobs for a Store that needs a configured guess — profile root or non-materialized Source."""

    spatial_step: float
    retention_interval: timedelta


@dataclass(frozen=True)
class OfferingDef:
    """What a profile may declare for one catalogue offering.

    A def selects and ranks; it never restates what the plugin declares. `impl` and optional
    `name` select a catalogue spec; omitted `name` uses the manifest's default offering.
    `priority` ranks this producer on the shared scale with calculators (default 0). `settings`
    overrides are opaque to everyone but the impl's `build`. `store` whole-spec-replaces the
    catalogue `StoreSpec` for a non-materialized Source. The secret is the manifest's slot,
    never this def's: declaring a keyed offering commits the profile to supplying that secret.
    """

    impl: str
    priority: int = 0
    name: str | None = None
    settings: Mapping[str, object] = field(default_factory=dict)
    store: StoreSpec | None = None


@dataclass(frozen=True)
class CalculatorDef:
    """What a profile may declare for one catalogue calculator.

    A def selects and ranks; it never restates what the plugin declares. `fn_id` selects a
    manifest; `priority` ranks on the shared producer scale (default 0); `name` is the variant
    (binder-defaults to `"default"`); `stored` is retention policy.
    """

    fn_id: str
    priority: int = 0
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


def secret_env_name(impl_id: str, slot: str) -> str:
    """The env var an operator sets for one impl's secret — the one home of the spelling."""
    return f"{_ENV_PREFIX}{impl_id.replace('-', '_').upper()}_{slot.upper()}"


def secrets_from_env(
    slots: Mapping[str, str], env_file: str | Path | None = _ENV_FILE
) -> dict[str, str]:
    """`impl_id` → secret value, read by derived name; empty or absent yields no entry.

    Reads only the names the declared slots derive — never a scan of the namespace. `os.environ`
    wins over the `.env` file, matching how the typed fields resolve.
    """
    from_file: Mapping[str, str | None] = dotenv_values(env_file) if env_file is not None else {}
    secrets: dict[str, str] = {}
    for impl_id, slot in slots.items():
        name = secret_env_name(impl_id, slot)
        value = os.environ.get(name) or from_file.get(name)
        if value:
            secrets[impl_id] = value
    return secrets
