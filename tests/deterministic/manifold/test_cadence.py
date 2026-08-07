"""CadenceDef — run anchor, expiration, and rolling valid_time window; RollingAxis geometry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from meteoscape.manifold.cadence import CadenceDef, RollingAxis
from meteoscape.manifold.domain import AxisName, Interval, RegularAxis


def test_cadence_anchor_expiration_and_valid_time() -> None:
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(minutes=20),
        max_lead=timedelta(hours=6),
    )
    # Publication of the 12:00 run is 12:20. Just before → still on 11:00 run.
    just_before = datetime(2026, 7, 11, 12, 19, tzinfo=UTC)
    assert cadence.anchor(just_before) == datetime(2026, 7, 11, 11, 0, tzinfo=UTC)

    at_publication = datetime(2026, 7, 11, 12, 20, tzinfo=UTC)
    assert cadence.anchor(at_publication) == datetime(2026, 7, 11, 12, 0, tzinfo=UTC)

    a = cadence.anchor(at_publication)
    assert cadence.expiration(at_publication) == a + timedelta(hours=1) + timedelta(minutes=20)
    assert cadence.valid_time(at_publication) == Interval(a, a + timedelta(hours=6))


NOON = datetime(2026, 7, 11, 12, tzinfo=UTC)
MIDNIGHT = datetime(2026, 7, 11, 0, tzinfo=UTC)
DAY = timedelta(hours=24)
HOURLY = CadenceDef(
    cadence=timedelta(hours=1), publication_latency=timedelta(0), max_lead=timedelta(hours=6)
)


def test_day_quantum_anchors_valid_time_at_midnight() -> None:
    """A shelf-quantized product: the availability window floors to the day, not the run."""
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(hours=1),
        max_lead=timedelta(hours=383),
        window_quantum=DAY,
    )
    assert cadence.valid_time(NOON) == Interval(MIDNIGHT, MIDNIGHT + timedelta(hours=383))


def test_day_quantum_window_holds_within_the_day_and_jumps_at_midnight() -> None:
    """Within the day the shelf is fixed; crossing midnight advances it by one quantum."""
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(hours=1),
        max_lead=timedelta(hours=383),
        window_quantum=DAY,
    )
    clock = _MovingClock(NOON)
    same_day = Interval(MIDNIGHT, MIDNIGHT + timedelta(hours=383))
    assert cadence.valid_time(clock.now()) == same_day
    clock.instant = NOON + timedelta(hours=11)
    assert cadence.valid_time(clock.now()) == same_day
    clock.instant = MIDNIGHT + DAY
    next_midnight = MIDNIGHT + DAY
    assert cadence.valid_time(clock.now()) == Interval(
        next_midnight, next_midnight + timedelta(hours=383)
    )


def test_window_quantum_does_not_touch_anchor_or_expiration() -> None:
    """Two clocks: the quantum shelves availability only; run identity and freshness stay on Δ/L."""
    shared = dict(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(hours=1),
        max_lead=timedelta(hours=383),
    )
    with_quantum = CadenceDef(**shared, window_quantum=DAY)
    without = CadenceDef(**shared)
    assert with_quantum.anchor(NOON) == without.anchor(NOON)
    assert with_quantum.expiration(NOON) == without.expiration(NOON)
    assert with_quantum.valid_time(NOON) != without.valid_time(NOON)


def test_omitted_window_quantum_is_run_anchored() -> None:
    """No quantum → valid_time is the run window; existing callers stay byte-identical."""
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(hours=1),
        max_lead=timedelta(hours=6),
        window_quantum=None,
    )
    assert cadence.window_quantum is None
    assert cadence.valid_time(NOON) == Interval(
        cadence.anchor(NOON), cadence.anchor(NOON) + timedelta(hours=6)
    )


@dataclass
class _MovingClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant


def test_rolling_axis_clips_to_the_lattice_its_series_arrives_on() -> None:
    """A clock-relative window materialises at its declared step, then the bounds move the edges."""
    axis = RollingAxis(AxisName.T, HOURLY, _MovingClock(NOON), step=timedelta(hours=1))
    assert axis.extent == Interval(NOON, NOON + timedelta(hours=6))

    # Bounds inside the window.
    assert axis.clip(Interval(NOON + timedelta(hours=2), NOON + timedelta(hours=4))) == RegularAxis(
        AxisName.T, NOON + timedelta(hours=2), timedelta(hours=1), 3, True
    )
    # Bounds wider than the window: the whole window, cell by cell.
    assert axis.clip(Interval(NOON - timedelta(days=1), NOON + timedelta(days=1))) == RegularAxis(
        AxisName.T, NOON, timedelta(hours=1), 7, True
    )
    # The window rolled past the bounds — the raced-empty answer.
    assert axis.clip(Interval(NOON - timedelta(days=2), NOON - timedelta(days=1))) is None


def test_rolling_axis_lattice_moves_with_the_clock() -> None:
    clock = _MovingClock(NOON)
    axis = RollingAxis(AxisName.T, HOURLY, clock, step=timedelta(hours=1))
    bounds = Interval(NOON, NOON + timedelta(hours=6))

    assert axis.clip(bounds) == RegularAxis(AxisName.T, NOON, timedelta(hours=1), 7, True)
    clock.instant = NOON + timedelta(hours=2)
    # The window is now [14:00, 20:00]; the same bounds keep only its overlapping head.
    assert axis.clip(bounds) == RegularAxis(
        AxisName.T, NOON + timedelta(hours=2), timedelta(hours=1), 5, True
    )
