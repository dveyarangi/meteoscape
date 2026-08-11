"""Provider timing and its clock-relative `valid_time` axis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..clock import Clock, floor_to
from .domain import Axis, AxisName, Interval, RegularAxis


@dataclass(frozen=True)
class CadenceDef:
    """Run timing plus the optional Shelf its availability window stands on."""

    cadence: timedelta
    publication_latency: timedelta
    max_lead: timedelta

    shelf: timedelta | None = None
    """The calendar unit this vendor's served window turns in — daily for a by-calendar-day product,
    hourly for one relabelled each hour; `None` when availability follows the run instead.

    `max_lead` is the window's *length*; the Shelf is the size of the *jumps its start makes* as the
    clock advances. It also fixes the phase the served lattice anchors to, which is why it must stay a
    whole boundary → ADR-0003. Declared by the vendor leaf and executed here; the `Reservoir` never
    consults it, because refetching is governed by `expiration` and the axis's own retention answer
    (ADR-0002).
    """

    def anchor(self, now: datetime) -> datetime:
        """The effective run at `now`: the latest run whose publication (`r + L`) has already passed."""
        return floor_to(now - self.publication_latency, self.cadence)

    def expiration(self, now: datetime) -> datetime:
        """When the next run publishes and supersedes this one (`A + Δ + L`) - the freshness edge."""
        return self.anchor(now) + self.cadence + self.publication_latency

    def valid_time(self, now: datetime) -> Interval[datetime]:
        """Return the availability window on its Shelf, or the run window when there is none."""
        base = floor_to(now, self.shelf) if self.shelf else self.anchor(now)
        return Interval(lower=base, upper=base + self.max_lead)


@dataclass(frozen=True)
class RollingAxis(Axis):
    """Clock-relative `valid_time`; `step` is series sampling, not run cadence."""

    name: AxisName
    cadence: CadenceDef
    clock: Clock
    step: timedelta

    @property
    def extent(self) -> Interval:
        return self.cadence.valid_time(self.clock.now())

    def clip(self, bounds: Interval | None) -> RegularAxis | None:
        """Materialize the current window at the series step, restricted to `bounds`.

        One clock read per call, so the whole window and a restriction of it are consistent within a
        call but not across two: whoever resolves must clip once and pass the resulting lattice on,
        never re-derive it from the axis.
        """
        window = self.extent
        materialized = RegularAxis(
            self.name,
            window.lower,
            self.step,
            (window.upper - window.lower) // self.step + 1,  # type: ignore[operator]
            cellular=True,
        )
        return materialized if bounds is None else materialized.clip(bounds)
