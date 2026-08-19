"""Live composite serving-order check — opt-in via `uv run pytest tests/parity`.

Composes the named providers in `--provider-order` and asserts provenance names the priority-0
impl. Reordering the argument inverts the expectation. Serving order only: a live vendor cannot
be forced to fault.
"""

from __future__ import annotations

import os
from datetime import timedelta
from typing import Any

import pytest
from fastmcp import Client

from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import Metronome
from meteoscape.config import ArbiterPolicy, CalculatorDef, OfferingDef, ProfileConfig, StoreSpec
from meteoscape.nodes.calculators import builtin as calculators
from meteoscape.nodes.catalog.providers import ProviderCatalog, ProviderManifest
from meteoscape.nodes.providers import builtin as providers
from meteoscape.server import compose

_LAT = 52.52
_LON = 13.41
_REQUEST = {"latitude": _LAT, "longitude": _LON}


def _order(request: pytest.FixtureRequest) -> tuple[str, ...]:
    raw = request.config.getoption("--provider-order")
    assert isinstance(raw, str)
    order = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not order:
        pytest.fail("--provider-order is empty")
    return order


def _manifests(order: tuple[str, ...], catalog: ProviderCatalog) -> list[ProviderManifest]:
    found: list[ProviderManifest] = []
    for impl in order:
        manifest = catalog.get(impl)
        if manifest is None:
            pytest.fail(f"unknown provider impl {impl!r}")
        found.append(manifest)
    return found


def _secrets(request: pytest.FixtureRequest, manifests: list[ProviderManifest]) -> dict[str, str]:
    collected: dict[str, str] = {}
    for manifest in manifests:
        if manifest.secret is None:
            continue
        value = request.config.getoption("--twc-api-key") or os.environ.get(
            "METEOSCAPE_TWC_API_KEY"
        )
        if not value:
            pytest.skip(
                "composite parity needs a key: pass --twc-api-key or set METEOSCAPE_TWC_API_KEY; "
                "neither is present"
            )
        assert isinstance(value, str)
        collected[manifest.impl_id] = value
    return collected


def _profile(order: tuple[str, ...]) -> ProfileConfig:
    offerings = tuple(OfferingDef(impl=impl, priority=index) for index, impl in enumerate(order))
    return ProfileConfig(
        offerings=offerings,
        calculators=(CalculatorDef(calculators.WIND_UV),),
        root_store=StoreSpec(spatial_step=0.0001, retention_interval=timedelta(days=14)),
        arbiter=ArbiterPolicy(),
    )


async def _forecast_payload(profile: ProfileConfig, secrets: dict[str, str]) -> dict[str, Any]:
    clock = Metronome()
    gateway = compose(profile, providers.CATALOG, calculators.CATALOG, secrets, clock)
    app = build_mcp_app(gateway, clock)
    async with Client(app) as client:
        result = await client.call_tool("forecast_hourly", _REQUEST)
    payload = result.data
    assert isinstance(payload, dict)
    return payload


@pytest.mark.asyncio
async def test_composite_serves_the_configured_priority_0(request: pytest.FixtureRequest) -> None:
    order = _order(request)
    manifests = _manifests(order, providers.CATALOG)
    payload = await _forecast_payload(_profile(order), _secrets(request, manifests))

    prefix = f"{manifests[0].provider_id}:"
    served = {name: block for name, block in payload.items() if name != "valid_time"}
    assert served
    for block in served.values():
        assert isinstance(block, dict)
        source = block["provenance"]["source"]
        assert source.startswith(prefix), f"{source} is not the priority-0 producer {prefix!r}"
