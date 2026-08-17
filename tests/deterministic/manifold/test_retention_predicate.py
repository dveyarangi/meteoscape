"""Retention predicate — `Axis.satisfied_by` / `RollingAxis` override (ADR-0002)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from meteoscape.manifold.cadence import CadenceDef, RollingAxis
from meteoscape.manifold.domain import (
    AxisName,
    ContinuousAxis,
    Interval,
    RegularAxis,
    SelectionDomain,
    SnappedAxis,
    VantageAxis,
    open_axes,
)

T0 = datetime(2026, 8, 17, 11, 0, tzinfo=UTC)
NOW = datetime(2026, 8, 17, 11, 42, tzinfo=UTC)
HOUR = timedelta(hours=1)


def _snap(lower: datetime, upper: datetime) -> SnappedAxis:
    return SnappedAxis(AxisName.T, Interval(lower, upper))


def _static(lower: datetime, upper: datetime) -> ContinuousAxis:
    return ContinuousAxis(AxisName.T, Interval(lower, upper))


@dataclass
class _Clock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant


def _rolling(*, shelf: timedelta = HOUR, max_lead: timedelta = 10 * HOUR) -> RollingAxis:
    """Declared window floors to `T0` at `NOW` under a 1h Shelf."""
    return RollingAxis(
        AxisName.T,
        CadenceDef(
            cadence=HOUR,
            publication_latency=timedelta(0),
            max_lead=max_lead,
            shelf=shelf,
        ),
        _Clock(NOW),
        step=HOUR,
    )


def test_static_axis_unsatisfied_when_holdings_short_at_either_edge() -> None:
    """Case E: a static corpus is a slice — a wider ask needs more data."""
    declared = _static(T0, T0 + 10 * HOUR)
    needed = _snap(T0 + 2 * HOUR, T0 + 8 * HOUR)
    short_trailing = _static(T0 + 2 * HOUR, T0 + 5 * HOUR)
    short_leading = _static(T0 + 4 * HOUR, T0 + 8 * HOUR)
    assert not declared.satisfied_by(short_trailing, needed)
    assert not declared.satisfied_by(short_leading, needed)


def test_static_axis_satisfied_when_holdings_contain_what_it_offers() -> None:
    declared = _static(T0, T0 + 10 * HOUR)
    needed = _snap(T0 + 2 * HOUR, T0 + 8 * HOUR)
    held = _static(T0 + 2 * HOUR, T0 + 8 * HOUR)
    assert declared.satisfied_by(held, needed)


def test_rolling_satisfied_when_holdings_short_at_leading_edge() -> None:
    """Case A (defect 1): the gap below the Holding was never published."""
    declared = _rolling()
    held = _static(T0 + HOUR, T0 + 10 * HOUR)
    needed = _snap(NOW, NOW + 3 * HOUR)
    assert declared.satisfied_by(held, needed)


def test_rolling_satisfied_when_holdings_short_at_horizon_while_ask_has_started() -> None:
    """Case B (defect 2): reach-advance is staleness — cadence, not the Shelf, governs refetch."""
    declared = _rolling()
    held = _static(T0 + HOUR, T0 + 9 * HOUR)
    needed = _snap(T0 + 2 * HOUR, T0 + 9 * HOUR + timedelta(minutes=30))
    assert declared.satisfied_by(held, needed)


def test_rolling_unsatisfied_when_holdings_fallen_entirely_behind_the_ask() -> None:
    """Case C: the horizon rule is not merely permissive — a Holding must have reached the ask."""
    declared = _rolling()
    held = _static(T0 - 5 * HOUR, T0 - HOUR)
    needed = _snap(NOW, NOW + 3 * HOUR)
    assert not declared.satisfied_by(held, needed)


def test_rolling_satisfied_when_ask_lies_wholly_below_the_holding() -> None:
    """Case D: refetching moves a rolling window further away — unservable, not unfetched."""
    declared = _rolling()
    held = _static(T0 + HOUR, T0 + 10 * HOUR)
    needed = _snap(T0 + timedelta(minutes=10), T0 + timedelta(minutes=50))
    assert declared.satisfied_by(held, needed)


def test_both_arms_clamp_needed_to_declared_reach() -> None:
    """An ask past what the axis offered does not make Holdings look insufficient."""
    static = _static(T0, T0 + 6 * HOUR)
    rolling = _rolling(max_lead=6 * HOUR)
    held = _static(T0, T0 + 6 * HOUR)
    past = _snap(T0 + HOUR, T0 + 10 * HOUR)
    assert static.satisfied_by(held, past)
    assert rolling.satisfied_by(held, past)


def test_want_none_is_satisfied_on_both_arms() -> None:
    """No overlap with the declaration → satisfied; the Reservoir's assert depends on this arm."""
    static = _static(T0, T0 + 6 * HOUR)
    rolling = _rolling(max_lead=6 * HOUR)
    held = _static(T0, T0 + 6 * HOUR)
    elsewhere = _snap(T0 + 8 * HOUR, T0 + 10 * HOUR)
    assert static.satisfied_by(held, elsewhere)
    assert rolling.satisfied_by(held, elsewhere)


def test_any_on_t_never_reaches_the_predicate() -> None:
    """Boundless T has no extent — `open_axes` is the guard that keeps `satisfied_by` off that path."""
    any_t = SnappedAxis(AxisName.T)
    domain = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 10.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 20.0, 1.0, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: any_t,
        }
    )
    assert AxisName.T in open_axes(domain)
    with pytest.raises(ValueError, match="open t member has no extent"):
        _rolling().satisfied_by(_static(T0, T0 + HOUR), any_t)
