"""`CoverageSet` — the multi-domain answer and its fold onto one enumerable Selection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

import pytest

from fakes import core_parameters, snapped_point_domain
from meteoscape.errors import CapabilityMismatch
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import EnumerableCapability
from meteoscape.manifold.core import Coverage, Selection
from meteoscape.manifold.coverage import CoverageRecord, CoverageSet
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import (
    AxisName,
    EnumerableAxis,
    GridDomain,
    Interval,
    RegularAxis,
    VantageAxis,
)
from meteoscape.manifold.provenance import (
    AtomicOrigin,
    PerParameter,
    Provenance,
    ProvenanceField,
    Uniform,
)
from meteoscape.parameters import AIR_TEMPERATURE, RELATIVE_HUMIDITY, WIND_U, ParameterId

NOON = datetime(2026, 7, 11, 12, tzinfo=UTC)
VANTAGE = VantageAxis(AxisName.Z, Interval(0.0, 10.0))
"""The vantage cell a request asks at — what native levels are relabelled onto."""


def _at(level: float) -> RegularAxis:
    """A native Z point cell, the way a tap declares one."""
    return RegularAxis(AxisName.Z, level, 1.0, 1, False)


def _grid(*, z: EnumerableAxis, hours: int = 4, start: datetime = NOON) -> GridDomain:
    """The v1 point+timeline shape: one X/Y point, one Z cell, `hours` ticks."""
    return GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
            AxisName.Z: z,
            AxisName.T: RegularAxis(AxisName.T, start, timedelta(hours=1), hours, True),
        }
    )


def _stamp(source: str = "open-meteo") -> Provenance:
    return Provenance(
        origin=AtomicOrigin(SourceKey(source, "default"), NOON),
        fetched_at=NOON,
        expiration=NOON + timedelta(hours=1),
    )


def _record(
    values: Mapping[ParameterId, Sequence[float]],
    *,
    domain: GridDomain,
    provenance: ProvenanceField | None = None,
) -> CoverageRecord:
    """One native record: the parameters sharing a Z cell, positional to `domain`."""
    table = core_parameters()
    return CoverageRecord(
        capability=EnumerableCapability(
            domain=domain, parameters={pid: table.get(pid) for pid in values}
        ),
        ranges={
            pid: ParameterData(values=list(series), present=None) for pid, series in values.items()
        },
        provenance=provenance or Uniform(_stamp()),
    )


@pytest.mark.asyncio
async def test_one_record_folds_onto_the_requested_cells() -> None:
    """The degenerate group: the single record cropped onto the ask, its native Z relabelled."""
    native = _record({AIR_TEMPERATURE: [18.0, 19.0, 20.0, 21.0]}, domain=_grid(z=_at(2.0)))
    target = _grid(z=VANTAGE, hours=2)

    answer = await CoverageSet((native,)).project(
        Selection(domain=target, parameters=frozenset({AIR_TEMPERATURE}))
    )

    assert isinstance(answer, Coverage)
    assert answer.domain == target
    assert list(answer.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0]


@pytest.mark.asyncio
async def test_records_on_differing_levels_merge_into_one_answer() -> None:
    """The multi-domain fold: temperature at 2 m beside wind at 10 m, one answer at the vantage."""
    plane = Uniform(_stamp())
    two_metre = _record(
        {AIR_TEMPERATURE: [18.0, 19.0, 20.0, 21.0]}, domain=_grid(z=_at(2.0)), provenance=plane
    )
    ten_metre = _record(
        {WIND_U: [-10.0, -11.0, -12.0, -13.0]}, domain=_grid(z=_at(10.0)), provenance=plane
    )
    target = _grid(z=VANTAGE, hours=3)

    answer = await CoverageSet((two_metre, ten_metre)).project(
        Selection(domain=target, parameters=frozenset({AIR_TEMPERATURE, WIND_U}))
    )

    assert isinstance(answer, Coverage)
    assert answer.domain == target
    assert set(answer.capability.parameters) == {AIR_TEMPERATURE, WIND_U}
    assert list(answer.ranges[AIR_TEMPERATURE].values) == [18.0, 19.0, 20.0]
    assert list(answer.ranges[WIND_U].values) == [-10.0, -11.0, -12.0]


@pytest.mark.asyncio
async def test_each_record_crops_against_its_own_ticks() -> None:
    """No record is privileged: a group whose records start an hour apart is folded honestly,
    not stacked on the first record's lattice."""
    from_noon = _record({AIR_TEMPERATURE: [18.0, 19.0, 20.0, 21.0]}, domain=_grid(z=_at(2.0)))
    from_one = _record(
        {WIND_U: [-10.0, -11.0, -12.0, -13.0]},
        domain=_grid(z=_at(10.0), start=NOON + timedelta(hours=1)),
    )
    target = _grid(z=VANTAGE, hours=2, start=NOON + timedelta(hours=1))

    answer = await CoverageSet((from_noon, from_one)).project(
        Selection(domain=target, parameters=frozenset({AIR_TEMPERATURE, WIND_U}))
    )

    assert isinstance(answer, Coverage)
    # 13:00 is the second tick of one series and the first of the other.
    assert list(answer.ranges[AIR_TEMPERATURE].values) == [19.0, 20.0]
    assert list(answer.ranges[WIND_U].values) == [-10.0, -11.0]


@pytest.mark.asyncio
async def test_one_shared_plane_survives_the_merge() -> None:
    """The one-fetch case: records stamped alike answer with the single plane the wire reads."""
    plane = Uniform(_stamp())
    two_metre = _record(
        {AIR_TEMPERATURE: [18.0]}, domain=_grid(z=_at(2.0), hours=1), provenance=plane
    )
    ten_metre = _record({WIND_U: [-10.0]}, domain=_grid(z=_at(10.0), hours=1), provenance=plane)

    answer = await CoverageSet((two_metre, ten_metre)).project(
        Selection(domain=_grid(z=VANTAGE, hours=1), parameters=frozenset({AIR_TEMPERATURE, WIND_U}))
    )

    assert isinstance(answer, Coverage)
    assert isinstance(answer.provenance, Uniform)


@pytest.mark.asyncio
async def test_differing_planes_become_per_parameter_provenance() -> None:
    """Records from separate fetches keep their own origin — each parameter's is its owner's."""
    early, late = _stamp("early"), _stamp("late")
    two_metre = _record(
        {AIR_TEMPERATURE: [18.0]}, domain=_grid(z=_at(2.0), hours=1), provenance=Uniform(early)
    )
    ten_metre = _record(
        {WIND_U: [-10.0]}, domain=_grid(z=_at(10.0), hours=1), provenance=Uniform(late)
    )

    answer = await CoverageSet((two_metre, ten_metre)).project(
        Selection(domain=_grid(z=VANTAGE, hours=1), parameters=frozenset({AIR_TEMPERATURE, WIND_U}))
    )

    assert isinstance(answer, Coverage)
    assert isinstance(answer.provenance, PerParameter)
    assert answer.provenance.summary(AIR_TEMPERATURE) == early
    assert answer.provenance.summary(WIND_U) == late


@pytest.mark.asyncio
async def test_a_set_folds_onto_enumerable_cells_only() -> None:
    """The carrier crops and merges; it homogenizes nothing, so bounds alone cannot address it."""
    group = CoverageSet((_record({AIR_TEMPERATURE: [18.0]}, domain=_grid(z=_at(2.0), hours=1)),))
    bounds = snapped_point_domain(start=NOON, end=NOON + timedelta(hours=1), lon=13.41, lat=52.52)

    with pytest.raises(CapabilityMismatch, match="enumerable"):
        await group.project(Selection(domain=bounds, parameters=frozenset({AIR_TEMPERATURE})))


@pytest.mark.asyncio
async def test_a_set_declines_a_parameter_no_record_holds() -> None:
    group = CoverageSet((_record({AIR_TEMPERATURE: [18.0]}, domain=_grid(z=_at(2.0), hours=1)),))

    with pytest.raises(CapabilityMismatch, match="wind_u"):
        await group.project(
            Selection(domain=_grid(z=VANTAGE, hours=1), parameters=frozenset({WIND_U}))
        )


def test_capability_reaches_each_parameter_on_its_own_native_domain() -> None:
    """What a group advertises: the disjoint union, every parameter at the geometry it arrived on."""
    two_metre = _grid(z=_at(2.0), hours=4)
    ten_metre = _grid(z=_at(10.0), hours=2)
    group = CoverageSet(
        (
            _record(
                {AIR_TEMPERATURE: [18.0, 19.0, 20.0, 21.0], RELATIVE_HUMIDITY: [50.0] * 4},
                domain=two_metre,
            ),
            _record({WIND_U: [-10.0, -11.0]}, domain=ten_metre),
        )
    )

    capability = group.capability

    assert set(capability.parameters) == {AIR_TEMPERATURE, RELATIVE_HUMIDITY, WIND_U}
    assert capability.reach(AIR_TEMPERATURE) is two_metre
    assert capability.reach(RELATIVE_HUMIDITY) is two_metre
    assert capability.reach(WIND_U) is ten_metre


def test_a_parameter_may_live_on_one_record_only() -> None:
    """Construction invariant: one native domain per parameter, so an owning record always exists."""
    two_metre = _record({AIR_TEMPERATURE: [18.0]}, domain=_grid(z=_at(2.0), hours=1))
    ten_metre = _record({AIR_TEMPERATURE: [17.0]}, domain=_grid(z=_at(10.0), hours=1))

    with pytest.raises(ValueError, match="air_temperature"):
        CoverageSet((two_metre, ten_metre))


@pytest.mark.asyncio
async def test_a_record_whose_cells_do_not_fit_the_ask_asserts_rather_than_mis_indexes() -> None:
    """A two-cell Z cannot be folded onto one vantage cell — and what comes back is the *engine's
    assert*, not a refusal this carrier promises.

    `NotImplementedError` here means admission let through a crop index arithmetic cannot express, so
    it is `serves` over-promising and concern #21 closes it there. Pinned only so the fold is known to
    stop rather than silently mis-index; deliberately **not** translated into `CapabilityMismatch`,
    which would claim the carrier holds nothing for this ask when it is holding the values and merely
    cannot move them (#36).
    """
    column = _record(
        {AIR_TEMPERATURE: [18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0]},
        domain=_grid(z=RegularAxis(AxisName.Z, 0.0, 1.0, 2, False)),
    )
    target = _grid(z=VANTAGE, hours=4)

    with pytest.raises(NotImplementedError):
        await CoverageSet((column,)).project(
            Selection(domain=target, parameters=frozenset({AIR_TEMPERATURE}))
        )
