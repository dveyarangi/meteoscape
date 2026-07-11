"""Settings projects ProfileConfig (OfferingDefs + secrets) from env scalars."""

from datetime import timedelta

from meteoscape.config import (
    ArbiterPolicy,
    OfferingDef,
    ProfileConfig,
    RootStoreSpec,
    Settings,
)


def test_defaults_emit_no_offerings_or_calculators() -> None:
    settings = Settings()
    assert settings.offerings() == ()
    assert settings.calculators() == ()
    assert settings.secrets() == {}


def test_open_meteo_enabled_emits_primary() -> None:
    settings = Settings(open_meteo_enabled=True)
    assert settings.offerings() == (OfferingDef(impl="open-meteo", name="best_match", priority=0),)


def test_twc_key_adds_fallback_offering() -> None:
    settings = Settings(twc_api_key="secret")
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
    settings = Settings(open_meteo_enabled=True, twc_api_key="secret")
    assert settings.offerings() == (
        OfferingDef(impl="open-meteo", name="best_match", priority=0),
        OfferingDef(
            impl="twc",
            name="default",
            priority=1,
            secret_ref="twc_api_key",
        ),
    )


def test_profile_projects_root_store_and_empty_calculators() -> None:
    settings = Settings()
    profile = settings.profile()
    assert profile == ProfileConfig(
        offerings=(),
        calculators=(),
        root_store=RootStoreSpec(
            spatial_step=0.0001,
            retention_interval=timedelta(days=14),
        ),
        arbiter=ArbiterPolicy(),
    )
