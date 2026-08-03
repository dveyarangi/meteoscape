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
HOURLY = CadenceDef(
    cadence=timedelta(hours=1), publication_latency=timedelta(0), max_lead=timedelta(hours=6)
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
