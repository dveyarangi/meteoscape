"""Provider timeline family — decode, the algebra's one home, and the geometry extension point."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from fakes import STOPPED, core_parameters
from meteoscape.errors import CapabilityMismatch
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import GranularCapability
from meteoscape.manifold.core import Coverage, Selection
from meteoscape.manifold.domain import (
    AxisName,
    Domain,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
    ScatterDomain,
    SelectionDomain,
    SnappedAxis,
    agreed_geometry,
    as_separable,
    ground,
)
from meteoscape.manifold.provenance import NEVER_EXPIRES, AtomicOrigin, Provenance
from meteoscape.nodes.providers import builtin  # noqa: F401 — loads the shipped family members
from meteoscape.nodes.providers.timeline import (
    HOURLY_STEP,
    Z_2M,
    PointSeriesTap,
    RollingTimeline,
    TapTable,
    TimelineDelivery,
    TimelineProvider,
    VendorVar,
    passthrough,
    pointwise,
)
from meteoscape.parameters import AIR_TEMPERATURE, ParameterId

_PLACE = (13.41, 52.52)
_NOON = datetime(2026, 7, 11, 12, tzinfo=UTC)
_FAMILY_ANSWERS = frozenset({"resolve", "stamp", "refresh", "capability", "__init__"})


def _own_names(cls: type) -> set[str]:
    """Names this class declares, ignoring language dunders (other than `__init__`) and ABC bookkeeping."""
    return {
        name
        for name in cls.__dict__
        if name == "__init__" or not (name.startswith("__") or name.startswith("_abc"))
    }


def _family() -> list[type]:
    """Every member Python has loaded, at any depth.

    `__subclasses__` is direct-only and sees just what has been imported, so the guard would pass
    vacuously for a member living in its own module: importing the shipped set is what makes the
    check real, and the recursion catches a member specialising another, such as a stamp-only
    geometry variant.
    """
    found: list[type] = []
    pending = list(TimelineProvider.__subclasses__())
    while pending:
        member = pending.pop()
        found.append(member)
        pending.extend(member.__subclasses__())
    return found


def test_family_members_do_not_reimplement_the_algebra() -> None:
    """The algebra has one home: a member overlapping `_interpret` or `_delivered` fails."""
    members = _family()
    # The shipped set is loaded above, so this also guards against the walk finding nothing.
    assert RollingTimeline in members
    for member in members:
        overlap = _own_names(member) & _own_names(TimelineProvider)
        unexpected = overlap - _FAMILY_ANSWERS
        assert not unexpected, f"{member.__name__} reimplements {sorted(unexpected)}"


class _CountingProbe:
    reports_units = False

    def __init__(self) -> None:
        self.retrieves = 0

    async def retrieve(
        self,
        *,
        longitude: float,
        latitude: float,
        over: Interval[datetime],
        variables: Sequence[str],
    ) -> TimelineDelivery:
        del longitude, latitude
        self.retrieves += 1
        ticks: list[datetime] = []
        tick = over.lower
        while tick <= over.upper:
            ticks.append(tick)
            tick += HOURLY_STEP
        return TimelineDelivery(
            valid_time=ticks,
            series={name: [1.0] * len(ticks) for name in variables},
        )


class _ScatterTimeline(TimelineProvider):
    """Fake family member: scatter reach, grounds a bounded-T ask via the matched place."""

    def __init__(self) -> None:
        taps = TapTable(
            (
                PointSeriesTap(
                    produces=AIR_TEMPERATURE,
                    vendor_vars=(VendorVar("t", "degC"),),
                    z=Z_2M,
                    decode=passthrough("t"),
                ),
            )
        )
        self.counting_probe = _CountingProbe()
        super().__init__(
            probe=self.counting_probe,
            taps=taps,
            step=HOURLY_STEP,
            parameters=core_parameters(),
            source_key=SourceKey("scatter-fake", "stations"),
        )
        self._clock = STOPPED
        self._scatter = ScatterDomain(
            points=(_PLACE, (0.0, 0.0)),
            t=RegularAxis(AxisName.T, _NOON, HOURLY_STEP, 4, False),
            z=RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
        )

    @property
    def capability(self) -> GranularCapability:
        reaches = {
            tap.produces: (self._parameters.get(tap.produces), self._scatter) for tap in self._taps
        }
        return GranularCapability(reaches=reaches)

    def resolve(self, request: Domain, parameters: Sequence[ParameterId]) -> GridDomain:
        try:
            stand_in = self._stand_in(request)
            wanted = agreed_geometry(
                (ground(request, stand_in) for _ in parameters),
                request=request,
            )
        except ValueError as exc:
            raise CapabilityMismatch(f"{self._source} cannot serve this selection: {exc}") from exc
        assert isinstance(wanted, GridDomain)
        return wanted

    def _stand_in(self, request: Domain) -> FootprintDomain:
        """The matched place as a point timeline — `ground` refuses a scatter itself."""
        requested = as_separable(request)
        if requested is None:
            raise ValueError("a snapped axis grounds only against separable geometry")
        longitude = requested.axis(AxisName.X).extent.lower
        latitude = requested.axis(AxisName.Y).extent.lower
        if (longitude, latitude) not in self._scatter.points:
            raise ValueError("no place within the requested bounds")
        return FootprintDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, longitude, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, latitude, 1.0, 1, False),
                AxisName.Z: self._scatter.z,
                AxisName.T: self._scatter.t,
            }
        )

    def stamp(self, wanted: GridDomain) -> Provenance:
        del wanted
        now = self._clock.now()
        return Provenance(
            origin=AtomicOrigin(self._source_key, None),
            fetched_at=now,
            expiration=NEVER_EXPIRES,
        )


def _scatter_selection() -> Selection:
    """A bounded-T ask at a member place — snapped T is what forces the answering geometry to be read."""
    return Selection(
        domain=SelectionDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, _PLACE[0], 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, _PLACE[1], 1.0, 1, False),
                AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
                AxisName.T: SnappedAxis(AxisName.T, Interval(_NOON, _NOON + timedelta(hours=3))),
            }
        ),
        parameters=frozenset({AIR_TEMPERATURE}),
    )


@pytest.mark.asyncio
async def test_scatter_member_grounds_a_bounded_t_request() -> None:
    """A non-separable reach answers a snapped-T ask through its own resolve, without the base changing.

    An exact GridDomain would not prove this: `ground` returns it by identity and never reads the
    answering geometry, so the rolling footprint path would succeed against a scatter too.
    """
    provider = _ScatterTimeline()
    assert isinstance(provider.capability.reach(AIR_TEMPERATURE), ScatterDomain)
    coverage = await provider.project(_scatter_selection())
    assert isinstance(coverage, Coverage)
    assert AIR_TEMPERATURE in coverage.ranges


@pytest.mark.asyncio
async def test_inherited_refresh_buys_nothing() -> None:
    """A fixed-facts member's `refresh` costs no fetch — counted, not read off an empty body.

    One projection, one retrieve: the `await self.refresh()` inside `project` added nothing. The
    vendor suites' `len(transport.requests) == 1` carry the same proof for `RollingTimeline`.
    """
    provider = _ScatterTimeline()
    await provider.refresh()
    assert provider.counting_probe.retrieves == 0
    await provider.project(_scatter_selection())
    assert provider.counting_probe.retrieves == 1


def test_null_yields_non_present_tick() -> None:
    decode = passthrough("temperature_2m")
    data = decode({"temperature_2m": [18.5, None, 19.1]})
    assert data.is_present(0) is True
    assert data.is_present(1) is False
    assert data.is_present(2) is True
    assert data.present is not None
    assert list(data.present) == [True, False, True]


def test_all_present_series_elides_mask() -> None:
    decode = passthrough("temperature_2m")
    data = decode({"temperature_2m": [18.5, 19.1]})
    assert data.present is None
    assert list(data.values) == [18.5, 19.1]


def test_fn_never_called_with_none() -> None:
    seen: list[tuple[float, ...]] = []

    def fn(*cells: float) -> float:
        seen.append(cells)
        assert all(c is not None for c in cells)
        return sum(cells)

    decode = pointwise("a", "b", fn=fn)
    data = decode({"a": [1.0, None, 3.0], "b": [10.0, 20.0, None]})
    assert seen == [(1.0, 10.0)]
    assert [data.is_present(i) for i in range(3)] == [True, False, False]


def test_two_var_absent_when_either_null() -> None:
    decode = pointwise("speed", "direction", fn=lambda s, d: s + d)
    data = decode({"speed": [1.0, None, 3.0], "direction": [10.0, 20.0, None]})
    assert data.is_present(0) is True
    assert data.is_present(1) is False
    assert data.is_present(2) is False
    assert data.values[0] == pytest.approx(11.0)
    assert math.isnan(data.values[1])
    assert math.isnan(data.values[2])
