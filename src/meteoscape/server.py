"""Composition root - the thin entrypoint.

Initializes observability and stands up the MCP surface. Owns the fixed composition sequence,
including the shared-clock `StoreFactory`; binders and the Weaver own graph decisions.
Availability lives in the builtin catalogues; this root declares only enablement.
"""

from __future__ import annotations

from collections.abc import Mapping

from .api.gateway import Gateway
from .api.mcp_app import build_mcp_app
from .clock import Clock, Metronome
from .config import (
    ArbiterPolicy,
    CalculatorDef,
    OfferingDef,
    ProfileConfig,
    Settings,
    secrets_from_env,
)
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
    woven = Weaver(StoreFactory(clock), clock).weave(
        ProfileDef(
            sources=sources,
            calculators=calc_registry,
            root_store=profile.root_store,
            arbiter=profile.arbiter,
        )
    )
    return Gateway(woven)


def main() -> None:
    init_observability()
    settings = Settings()
    clock = Metronome()
    gateway = compose(
        ProfileConfig(OFFERINGS, CALCULATORS, settings.root_store(), ArbiterPolicy()),
        providers.CATALOG,
        calculators.CATALOG,
        secrets_from_env(secret_slots(providers.CATALOG)),
        clock,
    )
    app = build_mcp_app(gateway, clock)
    app.run()
