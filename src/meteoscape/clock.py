"""`Clock` - the system time source, injected once at build into the leaves that read wall-clock time.

A `Clock` is a build-time dependency (like a configured logger), handed to `Provider`s by the Registry
at construction — never threaded through `project`. `Metronome` is the running clock: it floors
`now()` onto a coarse `resolution` grid, so the run anchor is a **step function** (no per-second
flicker) and any within-tick caching has a single natural home here. `StoppedClock` freezes one
instant for tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def floor_to(moment: datetime, step: timedelta) -> datetime:
    """Snap an aware-UTC `moment` down onto a `step`-spaced grid anchored at the Unix epoch."""
    return _EPOCH + (moment - _EPOCH) // step * step


@runtime_checkable
class Clock(Protocol):
    """A source of the current UTC instant - the only wall-clock read in the system."""

    def now(self) -> datetime: ...


@dataclass(frozen=True)
class Metronome:
    """The running clock: `datetime.now(UTC)` floored to `resolution`.

    Flooring quantizes time into ticks, so cadence-derived quantities stay constant within a tick.

    TODO(perf): the footprint filter reads `now()` per admission check (hundreds/request), each a
    `datetime.now()` syscall + floor. Since the tick is coarse, memoize `(floored, deadline)` gated on
    `time.monotonic()` so a request resolves one `now` (one syscall) and axes stay mutually consistent.
    Deferred - negligible vs provider I/O until a profiler says otherwise.
    """

    resolution: timedelta = timedelta(hours=1)

    def now(self) -> datetime:
        return floor_to(datetime.now(UTC), self.resolution)


@dataclass(frozen=True)
class StoppedClock:
    """A clock frozen at one `instant` - the deterministic test double."""

    instant: datetime

    def now(self) -> datetime:
        return self.instant
