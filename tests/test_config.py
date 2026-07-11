"""Settings projects ProfileConfig (OfferingDefs + secrets) from env scalars."""

from datetime import timedelta

from meteoscape.config import (
    ArbiterPolicy,
    CalculatorSpec,
    OfferingDef,
    ProfileConfig,
    RootStoreSpec,
    Settings,
)
from meteoscape.parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V


def test_default_offerings_open_meteo_only() -> None:
    settings = Settings()
    assert settings.offerings() == (OfferingDef(impl="open-meteo", name="best_match", priority=0),)
    assert settings.secrets() == {}


def test_twc_key_adds_fallback_offering() -> None:
    settings = Settings(twc_api_key="secret")
    assert settings.offerings() == (
        OfferingDef(impl="open-meteo", name="best_match", priority=0),
        OfferingDef(
            impl="twc",
            name="default",
            priority=1,
            secret_ref="twc_api_key",
        ),
    )
    assert settings.secrets() == {"twc_api_key": "secret"}


def test_open_meteo_can_be_disabled() -> None:
    settings = Settings(open_meteo_enabled=False, twc_api_key="secret")
    assert settings.offerings() == (
        OfferingDef(
            impl="twc",
            name="default",
            priority=1,
            secret_ref="twc_api_key",
        ),
    )


def test_profile_projects_root_store_and_wind_calculators() -> None:
    settings = Settings()
    profile = settings.profile()
    uv = frozenset({WIND_U, WIND_V})
    assert profile == ProfileConfig(
        offerings=settings.offerings(),
        calculators=(
            CalculatorSpec(output=WIND_SPEED, inputs=uv, fn_id="wind_speed"),
            CalculatorSpec(output=WIND_DIRECTION, inputs=uv, fn_id="wind_direction"),
        ),
        root_store=RootStoreSpec(
            spatial_step=0.1,
            retention_interval=timedelta(days=14),
        ),
        arbiter=ArbiterPolicy(),
    )
