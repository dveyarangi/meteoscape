"""ScatterDomain — joint X/Y membership, not an axis product."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fakes import snapped_point_domain
from meteoscape.manifold.domain import (
    AxisName,
    Interval,
    RegularAxis,
    ScatterDomain,
    SelectionDomain,
    SnappedAxis,
    VantageAxis,
    as_enumerable_axes,
    as_separable,
)

_NOON = datetime(2026, 7, 11, 12, tzinfo=UTC)
_RUSSEL = (-33.0129, -68.7473)
_MENDOZA = (-32.890, -68.845)


def _scatter(*points: tuple[float, float], hours: int = 4) -> ScatterDomain:
    return ScatterDomain(
        points=points,
        t=RegularAxis(AxisName.T, _NOON, timedelta(hours=1), hours, False),
        z=RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
    )


def test_scatter_admits_a_request_at_a_member_point() -> None:
    declared = _scatter(_RUSSEL, _MENDOZA)
    ask = snapped_point_domain(
        start=_NOON, end=_NOON + timedelta(hours=3), lon=_RUSSEL[0], lat=_RUSSEL[1]
    )
    assert declared.matches(ask) is True


def test_scatter_declines_a_cross_combination_of_member_coordinates() -> None:
    """X/Y are jointly matched: one station's longitude with another's latitude is not a place."""
    declared = _scatter(_RUSSEL, _MENDOZA)
    crossed = snapped_point_domain(
        start=_NOON,
        end=_NOON + timedelta(hours=3),
        lon=_RUSSEL[0],
        lat=_MENDOZA[1],
    )
    assert declared.matches(crossed) is False


def test_empty_scatter_is_capability_absence_not_a_vacuous_domain() -> None:
    with pytest.raises(ValueError, match="absence"):
        _scatter()


def test_duplicate_scatter_point_is_a_registry_bug() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        _scatter(_RUSSEL, _RUSSEL)


def test_scatter_t_and_z_match_per_axis() -> None:
    declared = _scatter(_RUSSEL)
    later = snapped_point_domain(
        start=_NOON + timedelta(days=1),
        end=_NOON + timedelta(days=1, hours=3),
        lon=_RUSSEL[0],
        lat=_RUSSEL[1],
    )
    assert declared.matches(later) is False

    high = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, _RUSSEL[0], 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, _RUSSEL[1], 1.0, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(100.0, 200.0)),
            AxisName.T: SnappedAxis(AxisName.T, Interval(_NOON, _NOON + timedelta(hours=3))),
        }
    )
    assert declared.matches(high) is False


def test_scatter_is_not_separable() -> None:
    declared = _scatter(_RUSSEL)
    assert as_separable(declared) is None
    assert as_enumerable_axes(declared) is None


def test_scatter_declines_a_boundless_spatial_ask() -> None:
    declared = _scatter(_RUSSEL)
    ask = SelectionDomain(
        axes={
            AxisName.X: SnappedAxis(AxisName.X),
            AxisName.Y: SnappedAxis(AxisName.Y),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: SnappedAxis(AxisName.T, Interval(_NOON, _NOON + timedelta(hours=3))),
        }
    )
    assert declared.matches(ask) is False


def test_scatter_declines_a_boxed_spatial_ask() -> None:
    declared = _scatter(_RUSSEL, _MENDOZA)
    ask = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, _RUSSEL[0], 0.1, 3, False),
            AxisName.Y: RegularAxis(AxisName.Y, _RUSSEL[1], 0.1, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: SnappedAxis(AxisName.T, Interval(_NOON, _NOON + timedelta(hours=3))),
        }
    )
    assert declared.matches(ask) is False


def test_scatter_equality_follows_points() -> None:
    a = _scatter(_RUSSEL, _MENDOZA)
    b = _scatter(_RUSSEL, _MENDOZA)
    assert a == b
    assert hash(a) == hash(b)
    assert a != _scatter(_RUSSEL)
