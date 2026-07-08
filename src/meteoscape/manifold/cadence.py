"""`CadenceDef` - a Provider's run-cadence declaration, the origin of every time-relative quantity -
plus `RollingAxis`, its geometry face.

From three per-provider facts - the run interval `Δ`, the `publication_latency` `L`, and the furthest
forward `max_lead` - one effective run `anchor` at request time `now` yields the run identity
(`issue_time`), freshness (`expiration`), and the footprint's rolling `valid_time` window. `RollingAxis`
projects that window into the `Axis` surface; it lives here rather than in `domain.py` so geometry stays
clock-free - the one clock-relative axis is isolated with the cadence it reads. See ADR-0003.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..clock import Clock, floor_to
from .domain import Axis, AxisName, Interval


@dataclass(frozen=True)
class CadenceDef:
    """Run interval `Δ`, publication latency `L`, and `max_lead` - the timing every derivation reads."""

    cadence: timedelta
    publication_latency: timedelta
    max_lead: timedelta

    def anchor(self, now: datetime) -> datetime:
        """The effective run at `now`: the latest run whose publication (`r + L`) has already passed."""
        return floor_to(now - self.publication_latency, self.cadence)

    def expiration(self, now: datetime) -> datetime:
        """When the next run publishes and supersedes this one (`A + Δ + L`) - the freshness edge."""
        return self.anchor(now) + self.cadence + self.publication_latency

    def valid_time(self, now: datetime) -> Interval[datetime]:
        """The run's forecast window `[A, A + max_lead]` - the footprint's rolling `valid_time` extent."""
        anchor = self.anchor(now)
        return Interval(lower=anchor, upper=anchor + self.max_lead)


@dataclass(frozen=True)
class RollingAxis(Axis):
    """The clock-anchored continuous axis: a `FootprintDomain`'s `valid_time` axis.

    `extent` resolves to the cadence's `valid_time(clock.now())` window `[A, A + max_lead]` at read, so
    this axis is deliberately **clock-relative** - the one intentional exception to axis-as-pure-geometry,
    isolated here (out of `domain.py`) with the cadence it reads. The `clock` is a build-time dependency
    the Provider injects into the single axis that rolls (never threaded through `project`); reconciling
    the anchor with the provider's real availability is concern #18 (ADR-0003 / ADR-0004).
    """

    name: AxisName
    cadence: CadenceDef
    clock: Clock

    @property
    def extent(self) -> Interval:
        return self.cadence.valid_time(self.clock.now())
