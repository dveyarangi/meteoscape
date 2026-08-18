"""Settings projects ProfileConfig (OfferingDefs + secrets) from env scalars."""

from __future__ import annotations

import ast
from datetime import timedelta
from pathlib import Path

from fakes import pinned_settings
from meteoscape.config import (
    ArbiterPolicy,
    CalculatorDef,
    OfferingDef,
    ProfileConfig,
    StoreSpec,
)
from meteoscape.parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V

_OM = OfferingDef(impl="open-meteo", priority=1)
_TWC = OfferingDef(impl="twc", priority=0, secret_ref="twc_api_key")
_WIND = CalculatorDef(
    outputs=frozenset({WIND_SPEED, WIND_DIRECTION}),
    inputs=frozenset({WIND_U, WIND_V}),
    fn_id="wind_uv",
    priority=0,
)
_CONFIG = Path(__file__).resolve().parents[2] / "src" / "meteoscape" / "config.py"


def test_defaults_emit_open_meteo_backstop() -> None:
    settings = pinned_settings()
    assert settings.offerings() == (_OM,)
    assert settings.calculators() == (_WIND,)
    assert settings.secrets() == {}


def test_open_meteo_disabled_emits_no_offerings() -> None:
    settings = pinned_settings(open_meteo_enabled=False)
    assert settings.offerings() == ()


def test_twc_key_adds_primary_offering() -> None:
    settings = pinned_settings(open_meteo_enabled=False, twc_api_key="secret")
    assert settings.offerings() == (_TWC,)
    assert settings.secrets() == {"twc_api_key": "secret"}
    assert settings.offerings()[0].name is None
    assert settings.offerings()[0].settings == {}


def test_open_meteo_and_twc_together() -> None:
    settings = pinned_settings(twc_api_key="secret")
    assert settings.offerings() == (_TWC, _OM)
    assert settings.offerings()[0].priority == 0
    assert settings.offerings()[1].priority == 1
    assert settings.offerings()[1].name is None


def test_profile_projects_root_store_and_open_meteo() -> None:
    settings = pinned_settings()
    profile = settings.profile()
    assert profile == ProfileConfig(
        offerings=(_OM,),
        calculators=(_WIND,),
        root_store=StoreSpec(
            spatial_step=0.0001,
            retention_interval=timedelta(days=14),
        ),
        arbiter=ArbiterPolicy(),
    )


def test_config_imports_nothing_from_nodes() -> None:
    tree = ast.parse(_CONFIG.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    leaked = [name for name in imported if "nodes" in name.split(".")]
    assert not leaked, f"config.py imports vendor modules: {leaked}"
