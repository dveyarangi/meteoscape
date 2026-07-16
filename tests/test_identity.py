"""SourceKey / CalculatorKey — producer identities."""

from __future__ import annotations

from meteoscape.identity import CalculatorKey, ProducerKey, SourceKey


def test_calculator_key_str_form() -> None:
    key = CalculatorKey(method="wind_uv", name="default")
    assert str(key) == "wind_uv:default"


def test_calculator_keys_distinct_by_method_and_name() -> None:
    a = CalculatorKey(method="wind_uv", name="default")
    b = CalculatorKey(method="wind_uv", name="variant")
    c = CalculatorKey(method="other", name="default")
    assert a != b
    assert a != c
    assert len({a, b, c}) == 3


def test_producer_key_accepts_source_or_calculator() -> None:
    source: ProducerKey = SourceKey(provider="open-meteo", dataset="best_match")
    calc: ProducerKey = CalculatorKey(method="wind_uv", name="default")
    assert str(source) == "open-meteo:best_match"
    assert str(calc) == "wind_uv:default"
