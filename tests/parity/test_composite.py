"""Live composite serving-order check — opt-in via `uv run pytest tests/parity`.

Composes the named providers in `--provider-order` and asserts provenance names the priority-0
impl. Reordering the argument inverts the expectation. Serving order only: a live vendor cannot
be forced to fault.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fastmcp import Client

from meteoscape.api.mcp_app import build_mcp_app
from meteoscape.clock import Metronome
from meteoscape.config import ArbiterPolicy, CalculatorDef, OfferingDef, ProfileConfig, StoreSpec
from meteoscape.nodes.catalog.providers import ProviderCatalog, ProviderManifest
from meteoscape.parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V
from meteoscape.server import CALCULATOR_CATALOG, PROVIDER_CATALOG, compose

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
    secrets: dict[str, str] = {}
    for manifest in manifests:
        if manifest.secret is None:
            continue
        slot = manifest.secret.name
        option = f"--{slot.replace('_', '-')}"
        try:
            value = request.config.getoption(option)
        except ValueError:
            value = None
        if not value:
            pytest.skip(f"composite parity needs {slot}: pass {option}; it is not present")
        assert isinstance(value, str)
        secrets[slot] = value
    return secrets


def _profile(order: tuple[str, ...], manifests: list[ProviderManifest]) -> ProfileConfig:
    offerings = tuple(
        OfferingDef(
            impl=impl,
            priority=index,
            secret_ref=manifest.secret.name if manifest.secret is not None else None,
        )
        for index, (impl, manifest) in enumerate(zip(order, manifests, strict=True))
    )
    return ProfileConfig(
        offerings=offerings,
        calculators=(
            CalculatorDef(
                outputs=frozenset({WIND_SPEED, WIND_DIRECTION}),
                inputs=frozenset({WIND_U, WIND_V}),
                fn_id="wind_uv",
                priority=0,
            ),
        ),
        root_store=StoreSpec(spatial_step=0.0001, retention_interval=timedelta(days=14)),
        arbiter=ArbiterPolicy(),
    )


async def _forecast_payload(profile: ProfileConfig, secrets: dict[str, str]) -> dict[str, Any]:
    clock = Metronome()
    gateway = compose(profile, PROVIDER_CATALOG, CALCULATOR_CATALOG, secrets, clock)
    app = build_mcp_app(gateway, clock)
    async with Client(app) as client:
        result = await client.call_tool("forecast_hourly", _REQUEST)
    payload = result.data
    assert isinstance(payload, dict)
    return payload


@pytest.mark.asyncio
async def test_composite_serves_the_configured_priority_0(request: pytest.FixtureRequest) -> None:
    order = _order(request)
    manifests = _manifests(order, PROVIDER_CATALOG)
    secrets = _secrets(request, manifests)
    payload = await _forecast_payload(_profile(order, manifests), secrets)

    prefix = f"{manifests[0].provider_id}:"
    served = {name: block for name, block in payload.items() if name != "valid_time"}
    assert served
    for block in served.values():
        assert isinstance(block, dict)
        source = block["provenance"]["source"]
        assert source.startswith(prefix), f"{source} is not the priority-0 producer {prefix!r}"
