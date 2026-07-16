"""Settings projects ProfileConfig (OfferingDefs + secrets) from env scalars."""

from datetime import timedelta

from meteoscape.config import (
    ArbiterPolicy,
    CalculatorDef,
    OfferingDef,
    ProfileConfig,
    Settings,
    StoreSpec,
)
from meteoscape.parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V

_OM = OfferingDef(impl="open-meteo", name="best_match", priority=0)
_WIND = CalculatorDef(
    outputs=frozenset({WIND_SPEED, WIND_DIRECTION}),
    inputs=frozenset({WIND_U, WIND_V}),
    fn_id="wind_uv",
    priority=0,
)


def test_defaults_emit_open_meteo_primary() -> None:
    settings = Settings()
    assert settings.offerings() == (_OM,)
    assert settings.calculators() == (_WIND,)
    assert settings.secrets() == {}


def test_open_meteo_disabled_emits_no_offerings() -> None:
    settings = Settings(open_meteo_enabled=False)
    assert settings.offerings() == ()


def test_twc_key_adds_fallback_offering() -> None:
    settings = Settings(open_meteo_enabled=False, twc_api_key="secret")
    assert settings.offerings() == (
        OfferingDef(
            impl="twc",
            name="default",
            priority=1,
            secret_ref="twc_api_key",
        ),
    )
    assert settings.secrets() == {"twc_api_key": "secret"}


def test_open_meteo_and_twc_together() -> None:
    settings = Settings(twc_api_key="secret")
    assert settings.offerings() == (
        _OM,
        OfferingDef(
            impl="twc",
            name="default",
            priority=1,
            secret_ref="twc_api_key",
        ),
    )


def test_profile_projects_root_store_and_open_meteo() -> None:
    settings = Settings()
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
