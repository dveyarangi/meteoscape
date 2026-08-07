"""Provider timing and its clock-relative `valid_time` axis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..clock import Clock, floor_to
from .domain import Axis, AxisName, Interval, RegularAxis


@dataclass(frozen=True)
class CadenceDef:
    """Run timing plus an optional independent quantum for the availability window."""

    cadence: timedelta
    publication_latency: timedelta
    max_lead: timedelta
    window_quantum: timedelta | None = None

    def anchor(self, now: datetime) -> datetime:
        """The effective run at `now`: the latest run whose publication (`r + L`) has already passed."""
        return floor_to(now - self.publication_latency, self.cadence)

    def expiration(self, now: datetime) -> datetime:
        """When the next run publishes and supersedes this one (`A + Δ + L`) - the freshness edge."""
        return self.anchor(now) + self.cadence + self.publication_latency

    def valid_time(self, now: datetime) -> Interval[datetime]:
        """Return the quantum-shelved availability window, or the run window when unshelved."""
        base = floor_to(now, self.window_quantum) if self.window_quantum else self.anchor(now)
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

    def clip(self, bounds: Interval) -> RegularAxis | None:
        """Materialize the current window at the series step, restricted to `bounds`."""
        window = self.extent
        materialized = RegularAxis(
            self.name,
            window.lower,
            self.step,
            (window.upper - window.lower) // self.step + 1,  # type: ignore[operator]
            cellular=True,
        )
        return materialized.clip(bounds)
