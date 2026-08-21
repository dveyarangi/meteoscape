"""Composition root - the thin entrypoint.

Initializes observability and stands up the MCP surface. Owns the fixed composition sequence,
including the shared-clock `StoreFactory`; binders and the Weaver own graph decisions.
Availability lives in the builtin catalogues; this root declares only enablement.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

from .api.mcp_app import build_mcp_app
from .clock import Clock, Metronome
from .config import (
    ArbiterPolicy,
    CalculatorDef,
    OfferingDef,
    ProfileConfig,
    StoreSpec,
    secrets_from_env,
)
from .gateway import Gateway
from .nodes.calculators import builtin as calculators
from .nodes.catalog.calculators import CalculatorCatalog
from .nodes.catalog.paramtable import StaticParameterTable
from .nodes.catalog.providers import ProviderCatalog, secret_slots
from .nodes.composition import CalculatorBinder, ProfileDef, SourceBinder
from .nodes.providers import builtin as providers
from .nodes.store import StoreFactory
from .nodes.weaver import Weaver
from .observability import init_observability

# The public server's profile — vendor-neutral, keyless; no global default exists (ADR-0005).
OFFERINGS: tuple[OfferingDef, ...] = (OfferingDef(providers.OPEN_METEO),)
CALCULATORS: tuple[CalculatorDef, ...] = (CalculatorDef(calculators.WIND_UV),)
ROOT_STORE = StoreSpec(
    # The best-view lattice: ~11 m cells, the fidelity floor the MCP edge publishes (one cell =>
    # identical values), and a 14-day eviction bound. Profile data, declared with the profile.
    spatial_step=0.0001,
    retention_interval=timedelta(days=14),
)


def compose(
    profile: ProfileConfig,
    provider_catalog: ProviderCatalog,
    calculator_catalog: CalculatorCatalog,
    secrets: Mapping[str, str],
    clock: Clock,
) -> Gateway:
    """Fixed pipeline: binders → ProfileDef → weave → Gateway. No branches."""
    parameters = StaticParameterTable.core()
    sources = SourceBinder(provider_catalog).build(profile.offerings, secrets, clock, parameters)
    calc_registry = CalculatorBinder(calculator_catalog).build(profile.calculators, parameters)
    stores = StoreFactory(clock)
    woven = Weaver(stores, clock).weave(
        ProfileDef(
            sources=sources,
            calculators=calc_registry,
            root_store=profile.root_store,
            arbiter=profile.arbiter,
        )
    )
    # Both construction sites, in construction order — reversed release then unwinds
    # outermost-first (root store → calculator store → source store → provider). Dropping
    # `stores.created` would break no test until docs/tickets/01-0145-persisting-store.md ships a
    # store that holds something.
    return Gateway(woven, sources.providers, stores.created)


def main() -> None:
    init_observability()
    clock = Metronome()
    gateway = compose(
        ProfileConfig(OFFERINGS, CALCULATORS, ROOT_STORE, ArbiterPolicy()),
        providers.CATALOG,
        calculators.CATALOG,
        secrets_from_env(secret_slots(providers.CATALOG)),
        clock,
    )
    app = build_mcp_app(gateway, clock)
    app.run()
