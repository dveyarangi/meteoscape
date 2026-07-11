"""Composition root - the thin entrypoint.

Initializes observability and stands up the MCP surface. Wires the full DAG
(catalogues + `Settings` → `ProfileConfig` → `SourceBinder.build` + `CalculatorBinder.build` →
`ProfileDef` → `Weaver.weave` → `Gateway`) but holds no construction logic of its own.
"""

from __future__ import annotations

from collections.abc import Mapping

from .api.gateway import Gateway
from .api.mcp_app import build_mcp_app
from .clock import Clock, Metronome
from .config import ProfileConfig, Settings
from .nodes.catalog.calculators import CalculatorCatalog
from .nodes.catalog.paramtable import StaticParameterTable
from .nodes.catalog.providers import ProviderCatalog
from .nodes.composition import CalculatorBinder, ProfileDef, SourceBinder
from .nodes.store import StoreFactory
from .nodes.weaver import Weaver
from .observability import init_observability

# Vendor modules each export a MANIFEST; the root assembles — data, not logic.
# Empty until Phase C registers Open-Meteo.
PROVIDER_CATALOG: ProviderCatalog = {}
CALCULATOR_CATALOG: CalculatorCatalog = {}


def compose(
    profile: ProfileConfig,
    catalog: ProviderCatalog,
    secrets: Mapping[str, str],
    clock: Clock,
    stores: StoreFactory,
) -> Gateway:
    """Fixed pipeline: binders → ProfileDef → weave → Gateway. No branches."""
    parameters = StaticParameterTable.core()
    sources = SourceBinder(catalog).build(profile.offerings, secrets, clock, parameters)
    calculators = CalculatorBinder(CALCULATOR_CATALOG).build(profile.calculators)
    woven = Weaver(stores).weave(
        ProfileDef(
            sources=sources,
            calculators=calculators,
            root_store=profile.root_store,
            arbiter=profile.arbiter,
        )
    )
    return Gateway(woven)


def main() -> None:
    init_observability()
    settings = Settings()
    compose(
        settings.profile(),
        PROVIDER_CATALOG,
        settings.secrets(),
        Metronome(),
        StoreFactory(),
    )
    app = build_mcp_app()
    app.run()
