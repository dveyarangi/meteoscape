"""Shipped plugin sets — availability as a system prop, not an edge prop."""

from meteoscape.nodes.calculators import builtin as calculators
from meteoscape.nodes.catalog.providers import secret_slots
from meteoscape.nodes.providers import builtin as providers
from meteoscape.parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V


def test_provider_builtin_handles_are_the_catalog_ids() -> None:
    assert set(providers.CATALOG) == {providers.TWC, providers.OPEN_METEO}
    assert providers.CATALOG[providers.TWC].impl_id == providers.TWC
    assert providers.CATALOG[providers.OPEN_METEO].impl_id == providers.OPEN_METEO


def test_calculator_builtin_handles_are_the_catalog_ids() -> None:
    assert set(calculators.CATALOG) == {calculators.WIND_UV}
    manifest = calculators.CATALOG[calculators.WIND_UV]
    assert manifest.fn_id == calculators.WIND_UV
    assert manifest.outputs == frozenset({WIND_SPEED, WIND_DIRECTION})
    assert manifest.inputs == frozenset({WIND_U, WIND_V})


def test_secret_slots_names_only_the_keyed_impls() -> None:
    """The bridge from availability to the env read: keyed impls declare, keyless ones do not."""
    assert secret_slots(providers.CATALOG) == {providers.TWC: "api_key"}
