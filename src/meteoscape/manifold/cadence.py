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
    clock advances, and the phase the served lattice anchors to (ADR-0003). The `Reservoir` never
    *decides* refetch from it — that is `expiration` plus the axis retention answer (ADR-0002) —
    though clamping the ask still reads the declared extent the Shelf helped form.
    """

    def __post_init__(self) -> None:
        # A rolling Holding refreshes only on expiry; cadence longer than the window lets it fall
        # entirely behind `now` between refreshes (ADR-0002 / ADR-0003).
        if self.cadence > self.max_lead:
            raise ValueError(f"cadence {self.cadence} must not exceed max_lead {self.max_lead}")

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

    def satisfied_by(self, held: Axis, needed: Axis) -> bool:
        """Satisfied unless my horizon has fallen behind the ask — reach-advance IS staleness here.

        My window is a pure function of the clock, so it only ever moves forward: the one way a
        Holding can fail an ask is by not having reached it yet. What it lacks *below* its own start
        was never published, and what it lacks *above* arrives with time, which `expiration` already
        governs — demanding containment would make my *Shelf*, not the declared cadence, the real
        refetch interval.

        Deliberately weaker than overlap: an ask lying wholly below the Holding is satisfied, because
        refetching moves the window further away. That ask is unservable, not unfetched, and the
        serving seam reports it as `CapabilityMismatch` rather than buying a useless fetch per call.
        """
        want = needed.extent.intersection(self.extent)  # type: ignore[arg-type]
        return want is None or want.lower <= held.extent.upper

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
