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
from .nodes.calculators.wind import MANIFEST as WIND_UV_MANIFEST
from .nodes.catalog.calculators import CalculatorCatalog
from .nodes.catalog.paramtable import StaticParameterTable
from .nodes.catalog.providers import ProviderCatalog
from .nodes.composition import CalculatorBinder, ProfileDef, SourceBinder
from .nodes.providers.open_meteo import MANIFEST as OPEN_METEO_MANIFEST
from .nodes.store import StoreFactory
from .nodes.weaver import Weaver
from .observability import init_observability

# Vendor / calculator modules each export a MANIFEST; the root assembles — data, not logic.
PROVIDER_CATALOG: ProviderCatalog = {
    OPEN_METEO_MANIFEST.impl_id: OPEN_METEO_MANIFEST,
}
CALCULATOR_CATALOG: CalculatorCatalog = {
    WIND_UV_MANIFEST.fn_id: WIND_UV_MANIFEST,
}


def compose(
    profile: ProfileConfig,
    providers: ProviderCatalog,
    calculators: CalculatorCatalog,
    secrets: Mapping[str, str],
    clock: Clock,
    stores: StoreFactory,
) -> Gateway:
    """Fixed pipeline: binders → ProfileDef → weave → Gateway. No branches."""
    parameters = StaticParameterTable.core()
    sources = SourceBinder(providers).build(profile.offerings, secrets, clock, parameters)
    calc_registry = CalculatorBinder(calculators).build(profile.calculators, parameters)
    woven = Weaver(stores).weave(
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
        settings.profile(),
        PROVIDER_CATALOG,
        CALCULATOR_CATALOG,
        settings.secrets(),
        clock,
        StoreFactory(),
    )
    app = build_mcp_app(gateway, clock, settings.default_horizon)
    app.run()
