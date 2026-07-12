"""RegularAxis / Domain behaviour — extent, enumeration, containment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from meteoscape.manifold.domain import (
    LATTICE_TOLERANCE,
    AxisName,
    Cell,
    ContinuousAxis,
    Domain,
    FootprintDomain,
    Interval,
    RegularAxis,
    RegularDomain,
    sub_lattice_offset,
)


def test_regular_axis_getitem_and_len() -> None:
    axis = RegularAxis(AxisName.X, 10.0, 0.5, 4, cellular=False)
    assert len(axis) == 4
    assert axis[0] == Cell(10.0, None)
    assert axis[1] == Cell(10.5, None)
    assert axis[3] == Cell(11.5, None)
    with pytest.raises(IndexError):
        _ = axis[4]
    with pytest.raises(IndexError):
        _ = axis[-1]

    cellular = RegularAxis(AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 3, True)
    assert cellular[0] == Cell(
        datetime(2026, 7, 11, tzinfo=UTC),
        Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 11, 1, tzinfo=UTC)),
    )
    assert cellular[2].bounds == Interval(
        datetime(2026, 7, 11, 2, tzinfo=UTC), datetime(2026, 7, 11, 3, tzinfo=UTC)
    )


def test_regular_axis_extent_is_tick_span() -> None:
    """Extent is the tick span — identical formula whether cellular or instant."""
    instants = RegularAxis(AxisName.X, 10.0, 0.5, 4, cellular=False)
    cellular = RegularAxis(AxisName.X, 10.0, 0.5, 4, cellular=True)
    expected = Interval(10.0, 11.5)  # anchor + (count-1)*step
    assert instants.extent == expected
    assert cellular.extent == expected

    time_axis = RegularAxis(
        AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 3, True
    )
    assert time_axis.extent == Interval(
        datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 11, 2, tzinfo=UTC)
    )


def test_regular_axis_rejects_invalid_count_and_step() -> None:
    with pytest.raises(ValueError, match="count"):
        RegularAxis(AxisName.X, 0.0, 1.0, 0, False)
    with pytest.raises(ValueError, match="step"):
        RegularAxis(AxisName.X, 0.0, 0.0, 1, False)
    with pytest.raises(ValueError, match="step"):
        RegularAxis(AxisName.X, 0.0, -1.0, 1, False)
    with pytest.raises(ValueError, match="step"):
        RegularAxis(AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(0), 1, False)


def _four_regular_axes() -> dict[AxisName, RegularAxis]:
    return {
        AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
        AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
        AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
        AxisName.T: RegularAxis(
            AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 1, False
        ),
    }


def test_regular_domain_requires_exactly_four_axes() -> None:
    RegularDomain(axes=_four_regular_axes())  # ok

    missing_t = {n: a for n, a in _four_regular_axes().items() if n is not AxisName.T}
    with pytest.raises(ValueError, match="four axes"):
        RegularDomain(axes=missing_t)

    mismatched = _four_regular_axes()
    mismatched[AxisName.X] = RegularAxis(AxisName.Y, 0.0, 1.0, 1, False)
    with pytest.raises(ValueError, match="name"):
        RegularDomain(axes=mismatched)

    footprint_axes = {
        AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
        AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
        AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
        AxisName.T: ContinuousAxis(
            AxisName.T,
            Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 18, tzinfo=UTC)),
        ),
    }
    FootprintDomain(axes=footprint_axes)  # ok
    with pytest.raises(ValueError, match="four axes"):
        FootprintDomain(axes={AxisName.X: footprint_axes[AxisName.X]})


def test_regular_domain_enumeration_order() -> None:
    """X → Y → Z → T nesting, T fastest; positional round-trip; point-timeline is time order."""
    domain = RegularDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 2, False),
            AxisName.Y: RegularAxis(AxisName.Y, 10.0, 1.0, 2, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 3, False
            ),
        }
    )
    assert len(domain) == 2 * 2 * 1 * 3
    points = list(domain.enumerate())
    assert len(points) == 12
    assert all(domain[i] == points[i] for i in range(12))

    # First point: all zeros; T advances fastest within the first spatial cell.
    assert points[0].cells[AxisName.X].coordinate == 0.0
    assert points[0].cells[AxisName.Y].coordinate == 10.0
    assert points[0].cells[AxisName.T].coordinate == datetime(2026, 7, 11, tzinfo=UTC)
    assert points[1].cells[AxisName.T].coordinate == datetime(2026, 7, 11, 1, tzinfo=UTC)
    assert points[2].cells[AxisName.T].coordinate == datetime(2026, 7, 11, 2, tzinfo=UTC)
    # After exhausting T, Y advances (Z count=1), then X.
    assert points[3].cells[AxisName.Y].coordinate == 11.0
    assert points[3].cells[AxisName.T].coordinate == datetime(2026, 7, 11, tzinfo=UTC)
    assert points[6].cells[AxisName.X].coordinate == 1.0

    # Degenerate point-timeline: count-1 spatial/Z → enumerates in time order.
    timeline = RegularDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 1.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 2.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 4, False
            ),
        }
    )
    assert [p.cells[AxisName.T].coordinate for p in timeline.enumerate()] == [
        datetime(2026, 7, 11, h, tzinfo=UTC) for h in range(4)
    ]


def test_footprint_domain_contains_by_extent() -> None:
    from meteoscape.clock import StoppedClock
    from meteoscape.manifold.cadence import CadenceDef, RollingAxis

    clock = StoppedClock(datetime(2026, 7, 11, 12, 0, tzinfo=UTC))
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(0),
        max_lead=timedelta(hours=6),
    )
    # A = 12:00, window_time = [12:00, 18:00]
    footprint = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-10.0, 10.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-5.0, 5.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: RollingAxis(AxisName.T, cadence, clock),
        }
    )

    inside = RegularDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 12, tzinfo=UTC), timedelta(hours=1), 3, False
            ),
        }
    )
    assert footprint.contains(inside) is True

    # One tick past A + max_lead — T extent upper is 18:00; a tick at 19:00 is outside.
    past = RegularDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 19, tzinfo=UTC), timedelta(hours=1), 1, False
            ),
        }
    )
    assert footprint.contains(past) is False

    # Before A.
    before = RegularDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 11, tzinfo=UTC), timedelta(hours=1), 1, False
            ),
        }
    )
    assert footprint.contains(before) is False

    class _NonSeparable(Domain):
        def contains(self, other: Domain) -> bool:
            return False

        def intersect(self, other: Domain) -> Domain:
            return self

    assert footprint.contains(_NonSeparable()) is False


def test_regular_domain_contains_by_extent() -> None:
    outer = RegularDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 5, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 5, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 10, False
            ),
        }
    )
    # Enumerable ⊆ enumerable by span (tick alignment is not contains' job).
    inner = RegularDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 1.0, 1.0, 2, False),
            AxisName.Y: RegularAxis(AxisName.Y, 2.0, 1.0, 2, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 2, tzinfo=UTC), timedelta(hours=1), 3, False
            ),
        }
    )
    assert outer.contains(inner) is True

    # Continuous other — per-axis span check.
    continuous = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(0.0, 4.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(0.0, 4.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(
                AxisName.T,
                Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 11, 9, tzinfo=UTC)),
            ),
        }
    )
    assert outer.contains(continuous) is True

    off_span = RegularDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 10.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 1, False
            ),
        }
    )
    assert outer.contains(off_span) is False


# --- hypothesis property cycles (session 0008) ---


@given(
    nx=st.integers(1, 3),
    ny=st.integers(1, 3),
    nz=st.integers(1, 2),
    nt=st.integers(1, 4),
)
def test_enumeration_round_trip_property(nx: int, ny: int, nz: int, nt: int) -> None:
    domain = RegularDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, nx, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, ny, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, nz, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), nt, False
            ),
        }
    )
    points = list(domain.enumerate())
    assert len(points) == len(domain)
    assert all(domain[i] == points[i] for i in range(len(domain)))


@given(tick=st.integers(0, 5), noise=st.floats(-2e-9, 2e-9, allow_nan=False, allow_infinity=False))
def test_float_alignment_tolerance_property(tick: int, noise: float) -> None:
    """Within ~half tolerance succeeds; beyond 2x fails. Boundary is float-fuzzy — leave a gap."""
    outer = RegularAxis(AxisName.X, 0.0, 1.0, 8, False)
    inner = RegularAxis(AxisName.X, float(tick) + noise, 1.0, 2, False)
    offset = sub_lattice_offset(outer, inner)
    if abs(noise) <= LATTICE_TOLERANCE * 0.5:
        assert offset == tick
    elif abs(noise) >= LATTICE_TOLERANCE * 2:
        assert offset is None
