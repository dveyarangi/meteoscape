"""Profile types and the env spelling: secrets are read by derived name — nothing else is."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from meteoscape.config import (
    CalculatorDef,
    OfferingDef,
    secret_env_name,
    secrets_from_env,
)

_CONFIG = Path(__file__).resolve().parents[2] / "src" / "meteoscape" / "config.py"
_SLOTS = {"twc": "api_key", "open-meteo": "api_key"}


def test_secret_env_name_is_the_operator_spelling() -> None:
    assert secret_env_name("open-meteo", "api_key") == "METEOSCAPE_OPEN_METEO_API_KEY"


def test_secrets_read_env_over_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("METEOSCAPE_TWC_API_KEY=fromfile\nMETEOSCAPE_OPEN_METEO_API_KEY=file\n")
    monkeypatch.setenv("METEOSCAPE_TWC_API_KEY", "fromenv")
    monkeypatch.delenv("METEOSCAPE_OPEN_METEO_API_KEY", raising=False)
    secrets = secrets_from_env(_SLOTS, env_file=env_file)
    assert secrets == {"twc": "fromenv", "open-meteo": "file"}


def test_only_declared_slots_are_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No namespace sweep: a var no declared slot names is never collected."""
    env_file = tmp_path / ".env"
    env_file.write_text("METEOSCAPE_TWC_API_KEY=k\nMETEOSCAPE_TWC_CADENCE_HOURS=3\n")
    monkeypatch.delenv("METEOSCAPE_TWC_API_KEY", raising=False)
    monkeypatch.delenv("METEOSCAPE_TWC_CADENCE_HOURS", raising=False)
    assert secrets_from_env({"twc": "api_key"}, env_file=env_file) == {"twc": "k"}


def test_empty_secret_is_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A blank .env line does not fill the slot."""
    env_file = tmp_path / ".env"
    env_file.write_text("METEOSCAPE_TWC_API_KEY=\n")
    monkeypatch.delenv("METEOSCAPE_TWC_API_KEY", raising=False)
    assert secrets_from_env({"twc": "api_key"}, env_file=env_file) == {}


def test_secret_stays_a_raw_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METEOSCAPE_TWC_API_KEY", "123")
    assert secrets_from_env({"twc": "api_key"}, env_file=None) == {"twc": "123"}


def test_no_env_file_reads_environ_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("METEOSCAPE_TWC_API_KEY", raising=False)
    assert secrets_from_env({"twc": "api_key"}, env_file=None) == {}


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


def test_config_module_names_no_builtin_impl() -> None:
    """Vendor-config purity, now that no typed field exists to name a vendor: the module's own
    source carries no builtin impl or fn id."""
    from meteoscape.nodes.calculators import builtin as calculators
    from meteoscape.nodes.providers import builtin as providers

    source = _CONFIG.read_text(encoding="utf-8")
    leaked = [ident for ident in (*providers.CATALOG, *calculators.CATALOG) if ident in source]
    assert not leaked, f"config.py names vendor ids: {leaked}"


def test_defs_take_builtin_handles_as_plain_ids_and_default_priority() -> None:
    from meteoscape.nodes.calculators import builtin as calculators
    from meteoscape.nodes.providers import builtin as providers

    offering = OfferingDef(providers.OPEN_METEO)
    assert offering.impl == "open-meteo"
    assert offering.priority == 0
    recipe = CalculatorDef(calculators.WIND_UV)
    assert recipe.fn_id == "wind_uv"
    assert recipe.priority == 0
