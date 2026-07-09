"""Settings derives SourceDefs and the secret map from env scalars."""

from meteoscape.config import Settings, SourceDef
from meteoscape.identity import SourceKey


def test_default_sources_open_meteo_only() -> None:
    settings = Settings()
    assert settings.sources() == (
        SourceDef(key=SourceKey("open-meteo", "best_match"), impl="open-meteo", priority=0),
    )
    assert settings.secrets() == {}


def test_twc_key_adds_fallback_source() -> None:
    settings = Settings(twc_api_key="secret")
    assert settings.sources() == (
        SourceDef(key=SourceKey("open-meteo", "best_match"), impl="open-meteo", priority=0),
        SourceDef(
            key=SourceKey("twc", "default"),
            impl="twc",
            priority=1,
            secret_ref="twc_api_key",
        ),
    )
    assert settings.secrets() == {"twc_api_key": "secret"}


def test_open_meteo_can_be_disabled() -> None:
    settings = Settings(open_meteo_enabled=False, twc_api_key="secret")
    assert settings.sources() == (
        SourceDef(
            key=SourceKey("twc", "default"),
            impl="twc",
            priority=1,
            secret_ref="twc_api_key",
        ),
    )
