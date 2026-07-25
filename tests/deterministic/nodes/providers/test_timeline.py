"""Provider timeline decode — pointwise presence rule."""

from __future__ import annotations

import math

import pytest

from meteoscape.nodes.providers.timeline import passthrough, pointwise


def test_null_yields_non_present_tick() -> None:
    decode = passthrough("temperature_2m")
    data = decode({"temperature_2m": [18.5, None, 19.1]})
    assert data.is_present(0) is True
    assert data.is_present(1) is False
    assert data.is_present(2) is True
    assert data.present is not None
    assert list(data.present) == [True, False, True]


def test_all_present_series_elides_mask() -> None:
    decode = passthrough("temperature_2m")
    data = decode({"temperature_2m": [18.5, 19.1]})
    assert data.present is None
    assert list(data.values) == [18.5, 19.1]


def test_fn_never_called_with_none() -> None:
    seen: list[tuple[float, ...]] = []

    def fn(*cells: float) -> float:
        seen.append(cells)
        assert all(c is not None for c in cells)
        return sum(cells)

    decode = pointwise("a", "b", fn=fn)
    data = decode({"a": [1.0, None, 3.0], "b": [10.0, 20.0, None]})
    assert seen == [(1.0, 10.0)]
    assert [data.is_present(i) for i in range(3)] == [True, False, False]


def test_two_var_absent_when_either_null() -> None:
    decode = pointwise("speed", "direction", fn=lambda s, d: s + d)
    data = decode({"speed": [1.0, None, 3.0], "direction": [10.0, 20.0, None]})
    assert data.is_present(0) is True
    assert data.is_present(1) is False
    assert data.is_present(2) is False
    assert data.values[0] == pytest.approx(11.0)
    assert math.isnan(data.values[1])
    assert math.isnan(data.values[2])
