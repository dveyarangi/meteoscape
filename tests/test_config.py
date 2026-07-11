"""Settings projects ProfileConfig (SourceDefs + secrets) from env scalars."""

from datetime import timedelta

from meteoscape.parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V
from meteoscape.config import (
    ArbiterPolicy,
    DerivationSpec,
    ProfileConfig,
    RootStoreSpec,
    Settings,
    SourceDef,
)


def test_default_sources_open_meteo_only() -> None:
    settings = Settings()
    assert settings.sources() == (
        SourceDef(impl="open-meteo", offering="best_match", priority=0),
    )
    assert settings.secrets() == {}


def test_twc_key_adds_fallback_source() -> None:
    settings = Settings(twc_api_key="secret")
    assert settings.sources() == (
        SourceDef(impl="open-meteo", offering="best_match", priority=0),
        SourceDef(
            impl="twc",
            offering="default",
            priority=1,
            secret_ref="twc_api_key",
        ),
    )
    assert settings.secrets() == {"twc_api_key": "secret"}


def test_open_meteo_can_be_disabled() -> None:
    settings = Settings(open_meteo_enabled=False, twc_api_key="secret")
    assert settings.sources() == (
        SourceDef(
            impl="twc",
            offering="default",
            priority=1,
            secret_ref="twc_api_key",
        ),
    )


def test_profile_projects_root_store_and_wind_derivations() -> None:
    settings = Settings()
    profile = settings.profile()
    uv = frozenset({WIND_U, WIND_V})
    assert profile == ProfileConfig(
        sources=settings.sources(),
        derivations=(
            DerivationSpec(output=WIND_SPEED, inputs=uv, fn_id="wind_speed"),
            DerivationSpec(output=WIND_DIRECTION, inputs=uv, fn_id="wind_direction"),
        ),
        root_store=RootStoreSpec(
            spatial_step=0.1,
            retention_interval=timedelta(days=14),
        ),
        arbiter=ArbiterPolicy(),
    )
