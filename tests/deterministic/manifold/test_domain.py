"""GridDomain / axis behaviour — extent, enumeration, containment, vantage matches."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fakes import STOPPED, footprint_domain, point_timeline_domain, snapped_point_domain
from meteoscape.manifold.cadence import CadenceDef, RollingAxis
from meteoscape.manifold.domain import (
    LATTICE_TOLERANCE,
    Axis,
    AxisName,
    Cell,
    ContinuousAxis,
    Domain,
    EnumerableAxis,
    EnumerableDomain,
    FootprintDomain,
    GridDomain,
    Interval,
    IntervalAxis,
    RegularAxis,
    SelectionDomain,
    SnappedAxis,
    VantageAxis,
    agreed_geometry,
    as_separable,
    contains_extents,
    first_incomparable,
    ground,
    open_axes,
    split_extents,
    sub_lattice_offset,
)


def test_interval_intersects() -> None:
    a = Interval(0.0, 10.0)
    assert a.intersects(Interval(5.0, 15.0)) is True
    assert a.intersects(Interval(10.0, 20.0)) is True  # touch at bound
    assert a.intersects(Interval(-5.0, 0.0)) is True
    assert a.intersects(Interval(2.0, 8.0)) is True  # contained
    assert a.intersects(Interval(11.0, 20.0)) is False
    assert a.intersects(Interval(-10.0, -1.0)) is False


def test_interval_intersection() -> None:
    a = Interval(0.0, 10.0)
    assert a.intersection(Interval(5.0, 15.0)) == Interval(5.0, 10.0)
    assert a.intersection(Interval(2.0, 8.0)) == Interval(2.0, 8.0)
    assert a.intersection(Interval(-5.0, 20.0)) == a
    assert a.intersection(Interval(10.0, 20.0)) == Interval(10.0, 10.0)  # touch → an instant
    assert a.intersection(Interval(11.0, 20.0)) is None


def test_interval_of_different_coordinate_kinds_never_meets() -> None:
    """A spatial span and a temporal one are disjoint, not a crash — a snapped X reaches this."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    space = Interval(-180.0, 180.0)
    time = Interval(noon, noon + timedelta(days=7))

    assert space.intersects(time) is False  # type: ignore[arg-type]
    assert time.intersects(space) is False  # type: ignore[arg-type]
    assert space.intersection(time) is None  # type: ignore[arg-type]

    # The two reachable readings of that: admission declines, and the clip leaves nothing.
    snapped_x = SnappedAxis(AxisName.X, time)
    declared_x = ContinuousAxis(AxisName.X, space)
    assert snapped_x.matches(declared_x) is False
    assert declared_x.clip(time) is None


def test_interval_axis_single_cell() -> None:
    axis = IntervalAxis(AxisName.Z, Interval(0.0, 12_000.0))
    assert len(axis) == 1
    assert axis.extent == Interval(0.0, 12_000.0)
    assert axis[0] == Cell(0.0, Interval(0.0, 12_000.0))
    with pytest.raises(IndexError):
        _ = axis[1]


def test_default_matches_is_containment() -> None:
    declared = ContinuousAxis(AxisName.Z, Interval(0.0, 10.0))
    inside = RegularAxis(AxisName.Z, 2.0, 1.0, 1, False)
    outside = RegularAxis(AxisName.Z, 20.0, 1.0, 1, False)
    span = IntervalAxis(AxisName.Z, Interval(0.0, 5.0))
    assert inside.matches(declared) is True
    assert outside.matches(declared) is False
    assert span.matches(declared) is True
    assert IntervalAxis(AxisName.Z, Interval(0.0, 20.0)).matches(declared) is False


def test_vantage_axis_matches_by_intersection() -> None:
    vantage = VantageAxis(AxisName.Z, Interval(0.0, 10.0))
    assert vantage.extent == Interval(0.0, 10.0)
    assert len(vantage) == 1
    assert vantage[0] == Cell(0.0, Interval(0.0, 10.0))

    sample_2m = RegularAxis(AxisName.Z, 2.0, 1.0, 1, False)
    sample_10m = RegularAxis(AxisName.Z, 10.0, 1.0, 1, False)
    sample_100m = RegularAxis(AxisName.Z, 100.0, 1.0, 1, False)
    cloud = IntervalAxis(AxisName.Z, Interval(0.0, 12_000.0))

    assert vantage.matches(sample_2m) is True
    assert vantage.matches(sample_10m) is True
    assert vantage.matches(cloud) is True
    assert vantage.matches(sample_100m) is False


def test_snapped_axis_rejects_naive_or_reversed_interval() -> None:
    """Aware equal bounds are legal (current-conditions instant); naive / reversed are not."""
    instant = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    equal = SnappedAxis(AxisName.T, Interval(instant, instant))
    assert equal.extent == Interval(instant, instant)

    with pytest.raises(ValueError, match="timezone-aware"):
        SnappedAxis(
            AxisName.T,
            Interval(datetime(2026, 7, 11, 12, 0), datetime(2026, 7, 11, 13, 0, tzinfo=UTC)),
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        SnappedAxis(
            AxisName.T,
            Interval(datetime(2026, 7, 11, 12, 0, tzinfo=UTC), datetime(2026, 7, 11, 13, 0)),
        )
    with pytest.raises(ValueError, match="lower"):
        SnappedAxis(
            AxisName.T,
            Interval(
                datetime(2026, 7, 11, 13, 0, tzinfo=UTC), datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
            ),
        )


def test_snapped_axis_matches_by_intersection() -> None:
    """Overlap / boundary-touch admit; disjoint rejects; containment of the declared is not required."""
    declared = ContinuousAxis(
        AxisName.T,
        Interval(datetime(2026, 7, 11, 12, tzinfo=UTC), datetime(2026, 7, 18, 12, tzinfo=UTC)),
    )
    overlap = SnappedAxis(
        AxisName.T,
        Interval(datetime(2026, 7, 15, tzinfo=UTC), datetime(2026, 7, 20, tzinfo=UTC)),
    )
    # Request wider than declared — still admits (intersection, not containment).
    wider = SnappedAxis(
        AxisName.T,
        Interval(datetime(2026, 7, 10, tzinfo=UTC), datetime(2026, 7, 20, tzinfo=UTC)),
    )
    touch_lower = SnappedAxis(
        AxisName.T,
        Interval(datetime(2026, 7, 10, tzinfo=UTC), datetime(2026, 7, 11, 12, tzinfo=UTC)),
    )
    touch_upper = SnappedAxis(
        AxisName.T,
        Interval(datetime(2026, 7, 18, 12, tzinfo=UTC), datetime(2026, 7, 19, tzinfo=UTC)),
    )
    before = SnappedAxis(
        AxisName.T,
        Interval(datetime(2026, 7, 1, tzinfo=UTC), datetime(2026, 7, 11, 11, tzinfo=UTC)),
    )
    after = SnappedAxis(
        AxisName.T,
        Interval(datetime(2026, 7, 18, 13, tzinfo=UTC), datetime(2026, 7, 25, tzinfo=UTC)),
    )

    assert overlap.matches(declared) is True
    assert wider.matches(declared) is True
    assert touch_lower.matches(declared) is True
    assert touch_upper.matches(declared) is True
    assert before.matches(declared) is False
    assert after.matches(declared) is False

    rolling = RollingAxis(
        AxisName.T,
        CadenceDef(timedelta(hours=1), timedelta(0), timedelta(days=7)),
        STOPPED,
        timedelta(hours=1),
    )
    # STOPPED = 2026-07-11 12:00 → window [12:00, +7d]; partial overlap admits.
    assert overlap.matches(rolling) is True
    assert before.matches(rolling) is False


def test_snapped_axis_is_not_enumerable() -> None:
    axis = SnappedAxis(
        AxisName.T,
        Interval(datetime(2026, 7, 11, 12, tzinfo=UTC), datetime(2026, 7, 12, tzinfo=UTC)),
    )
    assert isinstance(axis, Axis)
    assert not isinstance(axis, EnumerableAxis)
    # Standalone, not a `ContinuousAxis`: its bounds may be absent, a span's never are.
    assert not isinstance(axis, ContinuousAxis)


def test_boundless_snapped_member_is_accepted_on_any_axis() -> None:
    """`ANY` leaves the axis entirely to the producer — boundless is axis-generic (sits on Z too),
    and boundless is the default: a member without bounds is the open one."""
    for name in AxisName:
        member = SnappedAxis(name)
        assert member.interval is None


def test_bounded_spatial_snapped_member_is_rejected() -> None:
    """Temporal narrowing bites only when bounds are present — float bounds never construct."""
    with pytest.raises(ValueError, match="datetime"):
        SnappedAxis(AxisName.X, Interval(0.0, 1.0))  # type: ignore[arg-type]


def test_open_member_matches_every_declared_axis() -> None:
    open_z = SnappedAxis(AxisName.Z)
    assert open_z.matches(ContinuousAxis(AxisName.Z, Interval(0.0, 10.0))) is True
    assert open_z.matches(RegularAxis(AxisName.Z, 2.0, 1.0, 1, False)) is True
    assert open_z.matches(IntervalAxis(AxisName.Z, Interval(0.0, 12_000.0))) is True

    open_t = SnappedAxis(AxisName.T)
    rolling = RollingAxis(
        AxisName.T,
        CadenceDef(timedelta(hours=1), timedelta(0), timedelta(days=7)),
        STOPPED,
        timedelta(hours=1),
    )
    assert open_t.matches(rolling) is True


def test_open_member_has_no_extent_and_clips_to_itself() -> None:
    open_z = SnappedAxis(AxisName.Z)
    with pytest.raises(ValueError, match="open z member has no extent"):
        _ = open_z.extent
    # `clip` stays total for the `Axis` contract: nothing bounds the boundless.
    assert open_z.clip(Interval(0.0, 1.0)) is open_z
    assert open_z.clip(None) is open_z


def test_bounded_snapped_member_clip_without_bounds_is_itself() -> None:
    """A snapped member is never asked for a part of itself — no bounds changes nothing."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    member = SnappedAxis(AxisName.T, Interval(noon, noon + timedelta(hours=2)))
    assert member.clip(None) is member


def test_regular_axis_clip_keeps_the_lattice_and_moves_the_edges() -> None:
    """Anchor and step stay the axis's own; the bounds decide where it starts and stops."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    cells = RegularAxis(AxisName.T, noon, timedelta(hours=1), 6, True)  # 12:00 … 17:00

    def clip(lower: timedelta, upper: timedelta) -> Axis | None:
        return cells.clip(Interval(noon + lower, noon + upper))

    # Bounds wider than the axis trim nothing — a short axis is an honest short answer.
    assert clip(timedelta(days=-1), timedelta(days=1)) == cells
    # Both edges cut, on the tick.
    assert clip(timedelta(hours=2), timedelta(hours=4)) == RegularAxis(
        AxisName.T, noon + timedelta(hours=2), timedelta(hours=1), 3, True
    )
    # A cellular tick owns the span that follows it, so a mid-cell bound keeps its own cell.
    assert clip(timedelta(minutes=30), timedelta(hours=2, minutes=45)) == RegularAxis(
        AxisName.T, noon, timedelta(hours=1), 3, True
    )
    # An instant lands on the single cell containing it.
    assert clip(timedelta(hours=3), timedelta(hours=3)) == RegularAxis(
        AxisName.T, noon + timedelta(hours=3), timedelta(hours=1), 1, True
    )
    # Disjoint either way — nothing survives.
    assert clip(timedelta(days=-2), timedelta(days=-1)) is None
    assert clip(timedelta(days=1), timedelta(days=2)) is None


def test_regular_axis_clip_of_instants_keeps_only_ticks_inside_the_bounds() -> None:
    """`cellular=False` ticks own no span, so a bound between ticks excludes the one behind it."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    instants = RegularAxis(AxisName.T, noon, timedelta(hours=1), 6, False)

    assert instants.clip(
        Interval(noon + timedelta(minutes=30), noon + timedelta(hours=2, minutes=45))
    ) == RegularAxis(AxisName.T, noon + timedelta(hours=1), timedelta(hours=1), 2, False)
    # Bounds falling entirely between two ticks hold nothing.
    assert (
        instants.clip(Interval(noon + timedelta(minutes=30), noon + timedelta(minutes=45))) is None
    )


def test_regular_axis_clip_is_coordinate_generic() -> None:
    """One expression serves both coordinate kinds — m4 adds no temporal narrowing (concern #23)."""
    degrees = RegularAxis(AxisName.X, 0.0, 1.0, 5, False)  # 0.0 … 4.0
    assert degrees.clip(Interval(1.0, 3.0)) == RegularAxis(AxisName.X, 1.0, 1.0, 3, False)
    assert degrees.clip(Interval(10.0, 20.0)) is None


def test_regular_axis_clip_without_bounds_is_the_axis_entire() -> None:
    """No bounds = nothing to restrict — `ANY` takes the same verb with an empty argument."""
    cells = RegularAxis(AxisName.X, 0.0, 1.0, 5, False)
    assert cells.clip(None) is cells


def test_regular_axis_clip_absorbs_float_noise_at_a_cell_edge() -> None:
    """A bound float-noise off a cell edge clips into the containing cell.

    `0.3 / 0.1 == 2.9999999999999996`: a raw floor lands one cell early; the shared index-space
    tolerance (`LATTICE_TOLERANCE`) pulls it onto the edge it means.
    """
    cells = RegularAxis(AxisName.X, 0.0, 0.1, 5, cellular=True)  # 0.0 … 0.4
    assert cells.clip(Interval(0.3, 0.4)) == RegularAxis(
        AxisName.X, 0.0 + 3 * 0.1, 0.1, 2, cellular=True
    )

    # The instant kind reads the same edge: an upper bound at a tick keeps that tick.
    instants = RegularAxis(AxisName.X, 0.0, 0.1, 5, cellular=False)
    assert instants.clip(Interval(0.0, 0.3)) == RegularAxis(AxisName.X, 0.0, 0.1, 4, cellular=False)


def test_one_boundary_tolerance_policy() -> None:
    """Guard: one tolerance constant, referenced by both alignment reads — a second diverging
    constant fails here (RFC 0011)."""
    import inspect
    import re

    from meteoscape.manifold import domain as domain_module

    constants = re.findall(
        r"^_?\w*TOLERANCE\w*\s*=", inspect.getsource(domain_module), flags=re.MULTILINE
    )
    assert constants == ["LATTICE_TOLERANCE ="]
    assert "LATTICE_TOLERANCE" in inspect.getsource(RegularAxis.clip)
    assert "LATTICE_TOLERANCE" in inspect.getsource(sub_lattice_offset)


def test_interval_axis_clip_is_whole_or_nothing() -> None:
    """A single cell is never subdivided: bounds reaching into it keep it entire."""
    column = IntervalAxis(AxisName.Z, Interval(0.0, 12_000.0))
    assert column.clip(Interval(2_000.0, 3_000.0)) is column
    assert column.clip(Interval(-100.0, 0.0)) is column  # touch admits, as `intersects` does
    assert column.clip(Interval(12_001.0, 20_000.0)) is None
    assert column.clip(None) is column

    vantage = VantageAxis(AxisName.Z, Interval(0.0, 10.0))
    assert vantage.clip(Interval(5.0, 50.0)) is vantage
    assert vantage.clip(None) is vantage


def test_continuous_axis_clip_stays_a_span() -> None:
    """No cells appear from nowhere — which is why grounding a snapped member here declines."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    span = ContinuousAxis(AxisName.T, Interval(noon, noon + timedelta(days=7)))

    part = span.clip(Interval(noon + timedelta(days=1), noon + timedelta(days=30)))
    assert part == ContinuousAxis(
        AxisName.T, Interval(noon + timedelta(days=1), noon + timedelta(days=7))
    )
    assert not isinstance(part, EnumerableAxis)
    assert span.clip(Interval(noon - timedelta(days=2), noon - timedelta(days=1))) is None
    assert span.clip(None) is span


def _delivered(t: RegularAxis) -> GridDomain:
    """A delivered record's geometry — the post-fetch thing a request grounds against."""
    return GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
            AxisName.T: t,
        }
    )


def test_ground_passes_pins_and_takes_the_clipped_lattice() -> None:
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    request = snapped_point_domain(start=noon + timedelta(hours=1), end=noon + timedelta(hours=2))
    delivered = _delivered(RegularAxis(AxisName.T, noon, timedelta(hours=1), 6, True))

    grounded = ground(request, delivered)
    assert isinstance(grounded, GridDomain)
    # Pinned members are the answer already — identity, not a rebuild.
    assert grounded.axis(AxisName.X) is request.axis(AxisName.X)
    assert grounded.axis(AxisName.Y) is request.axis(AxisName.Y)
    assert grounded.axis(AxisName.Z) is request.axis(AxisName.Z)
    assert grounded.axis(AxisName.T) == RegularAxis(
        AxisName.T, noon + timedelta(hours=1), timedelta(hours=1), 2, True
    )


def test_ground_answers_an_open_member_with_the_answering_axis_whole() -> None:
    """`ANY` — the producer answers at its own native cells, however far they reach (T and Z)."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    request = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
            AxisName.Z: SnappedAxis(AxisName.Z),
            AxisName.T: SnappedAxis(AxisName.T),
        }
    )
    assert footprint_domain(STOPPED).matches(request) is True  # open members admit at admission
    timeline = RegularAxis(AxisName.T, noon, timedelta(hours=1), 6, True)
    delivered = _delivered(timeline)

    grounded = ground(request, delivered)
    assert isinstance(grounded, GridDomain)
    assert grounded.axis(AxisName.T) is timeline
    assert grounded.axis(AxisName.Z) is delivered.axis(AxisName.Z)
    assert grounded.axis(AxisName.X) is request.axis(AxisName.X)


def test_ground_answers_an_open_t_against_a_rolling_footprint() -> None:
    """Pre-fetch: a boundless T materializes the live window once — the gap decision 1 closes."""
    request = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: SnappedAxis(AxisName.T),
        }
    )
    footprint = footprint_domain(STOPPED)
    grounded = ground(request, footprint)
    assert isinstance(grounded, GridDomain)
    # STOPPED = 2026-07-11 12:00; fakes cadence max_lead = 7d at hourly step.
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    assert grounded.axis(AxisName.T) == RegularAxis(
        AxisName.T, noon, timedelta(hours=1), 7 * 24 + 1, True
    )
    assert grounded.axis(AxisName.Z) is request.axis(AxisName.Z)


def test_ground_declines_an_open_member_against_a_declared_span() -> None:
    """Cells are still ground's requirement: `ANY` against a span declines like a bounded member."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    request = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: SnappedAxis(AxisName.T),
        }
    )
    span_t = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(noon, noon + timedelta(days=7))),
        }
    )
    with pytest.raises(ValueError, match="a snapped t needs cells"):
        ground(request, span_t)


def test_ground_declines_when_nothing_survives_the_clip() -> None:
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    request = snapped_point_domain(start=noon + timedelta(hours=1), end=noon + timedelta(hours=2))
    elsewhere = _delivered(
        RegularAxis(AxisName.T, noon + timedelta(days=1), timedelta(hours=1), 3, True)
    )
    with pytest.raises(ValueError, match="no t within the requested bounds"):
        ground(request, elsewhere)


def test_ground_declines_an_answering_axis_without_cells() -> None:
    """The snapped X/Y case: a declared span clips to a span, and a span has no cells to take."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    request = snapped_point_domain(start=noon + timedelta(hours=1), end=noon + timedelta(hours=2))
    span_t = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(noon, noon + timedelta(days=7))),
        }
    )
    with pytest.raises(ValueError, match="snapped t needs cells"):
        ground(request, span_t)


def test_ground_declines_a_snapped_spatial_axis_as_disjoint() -> None:
    """`SnappedAxis` is temporal by type, so its bounds cannot address a spatial axis at all."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    request = SelectionDomain(
        axes={
            AxisName.X: SnappedAxis(AxisName.X, Interval(noon, noon + timedelta(hours=2))),
            AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: RegularAxis(AxisName.T, noon, timedelta(hours=1), 2, False),
        }
    )
    with pytest.raises(ValueError, match="no x within the requested bounds"):
        ground(request, footprint_domain(STOPPED))


def test_ground_reads_the_answering_geometry_only_for_snapped_members() -> None:
    """Totality: a snapped member needs a per-axis read, identity needs nothing at all."""
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)

    class _NonSeparable(Domain):
        def matches(self, other: Domain) -> bool:
            return False

        def intersect(self, other: Domain) -> Domain:
            raise NotImplementedError

    snapped = snapped_point_domain(start=noon, end=noon + timedelta(hours=2))
    with pytest.raises(ValueError, match="separable"):
        ground(snapped, _NonSeparable())

    pinned = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 1.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 2.0, 1.0, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: RegularAxis(AxisName.T, noon, timedelta(hours=1), 2, False),
        }
    )
    grounded = ground(pinned, _NonSeparable())
    assert isinstance(grounded, GridDomain)
    assert grounded.axes == pinned.axes


def test_ground_of_an_exact_request_is_identity() -> None:
    """An exact request is already its own answer — the identity that collapses the mode branch."""
    grid = point_timeline_domain()
    assert ground(grid, footprint_domain(STOPPED)) is grid


def test_ground_declines_a_declared_geometry_as_a_request() -> None:
    """Only the request side of the seam grounds: a footprint is what one grounds *against*."""
    with pytest.raises(ValueError, match="not a request"):
        ground(footprint_domain(STOPPED), point_timeline_domain())


def test_agreed_geometry_folds_resolutions_that_agree() -> None:
    """One project answers with one geometry on bounded axes (ADR-0001) — disagreement names the axis."""
    first = point_timeline_domain()  # an exact request leaves no axis open, so nothing may differ
    agreed = agreed_geometry([first, point_timeline_domain()], request=first)
    assert agreed is first
    with pytest.raises(ValueError, match="disagree on t"):
        agreed_geometry([first, point_timeline_domain(hours=3)], request=first)
    with pytest.raises(ValueError, match="no geometry"):
        agreed_geometry([], request=first)


def test_agreed_geometry_needs_axes_only_for_differing_members() -> None:
    """Separability is the precondition of comparing differing members, not of publishing agreeing
    ones — an exact non-separable request grounds by identity everywhere (concern #12, target role)."""

    class _CurvilinearExact(EnumerableDomain):
        def matches(self, other: Domain) -> bool:
            return False

        def intersect(self, other: Domain) -> Domain:
            raise NotImplementedError

        def __getitem__(self, index: int):
            raise IndexError(index)

        def __len__(self) -> int:
            return 0

        def enumerate(self):
            return iter(())

    exact = _CurvilinearExact()
    assert agreed_geometry([exact, exact], request=exact) is exact
    with pytest.raises(ValueError, match="axes"):
        agreed_geometry([exact, point_timeline_domain()], request=exact)


def test_agreed_geometry_licenses_difference_on_open_axes() -> None:
    """Axes the request left open let resolutions differ; the first stands for the bounded shape."""
    at_2m = point_timeline_domain()
    at_10m = GridDomain(
        axes={
            AxisName.X: at_2m.axis(AxisName.X),
            AxisName.Y: at_2m.axis(AxisName.Y),
            AxisName.Z: RegularAxis(AxisName.Z, 10.0, 1.0, 1, False),
            AxisName.T: at_2m.axis(AxisName.T),
        }
    )
    open_z = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
            AxisName.Z: SnappedAxis(AxisName.Z),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 12, tzinfo=UTC), timedelta(hours=1), 1, True
            ),
        }
    )
    assert agreed_geometry([at_2m, at_10m], request=open_z) is at_2m
    # The same difference is a disagreement once the request pins Z.
    with pytest.raises(ValueError, match="disagree on z"):
        agreed_geometry([at_2m, at_10m], request=at_2m)


def test_open_axes_names_boundless_snapped_members() -> None:
    noon = datetime(2026, 7, 11, 12, tzinfo=UTC)
    open_zt = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
            AxisName.Z: SnappedAxis(AxisName.Z),
            AxisName.T: SnappedAxis(AxisName.T),
        }
    )
    assert open_axes(open_zt) == frozenset({AxisName.Z, AxisName.T})
    bounded = snapped_point_domain(start=noon, end=noon + timedelta(hours=2))
    assert open_axes(bounded) == frozenset()
    assert open_axes(point_timeline_domain()) == frozenset()


def test_selection_domain_four_axes_and_axis_access() -> None:
    domain = snapped_point_domain(
        start=datetime(2026, 7, 11, 12, tzinfo=UTC),
        end=datetime(2026, 7, 12, tzinfo=UTC),
        lon=13.41,
        lat=52.52,
    )
    assert isinstance(domain.axis(AxisName.T), SnappedAxis)
    assert domain.axis(AxisName.X).extent.lower == 13.41
    assert not isinstance(domain, EnumerableDomain)

    with pytest.raises(ValueError, match="four axes"):
        SelectionDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, 1.0, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, 2.0, 1.0, 1, False),
                AxisName.T: SnappedAxis(
                    AxisName.T,
                    Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 12, tzinfo=UTC)),
                ),
            }
        )
    with pytest.raises(ValueError, match="name"):
        SelectionDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, 1.0, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, 2.0, 1.0, 1, False),
                AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
                AxisName.T: SnappedAxis(
                    AxisName.X,  # mismatched name
                    Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 12, tzinfo=UTC)),
                ),
            }
        )


def test_selection_domain_matches_totality() -> None:
    domain = snapped_point_domain(
        start=datetime(2026, 7, 11, 12, tzinfo=UTC),
        end=datetime(2026, 7, 12, tzinfo=UTC),
    )

    class _NonSeparable(Domain):
        def matches(self, other: Domain) -> bool:
            return False

        def intersect(self, other: Domain) -> Domain:
            raise NotImplementedError

    assert domain.matches(_NonSeparable()) is False


def test_footprint_matches_snapped_selection_by_intersection() -> None:
    """Admission needs no new engine code — Footprint.matches folds request-side SnappedAxis.matches."""
    footprint = footprint_domain(STOPPED)
    overlapping = snapped_point_domain(
        start=datetime(2026, 7, 12, tzinfo=UTC),
        end=datetime(2026, 7, 20, tzinfo=UTC),
        lon=13.41,
        lat=52.52,
    )
    no_overlap = snapped_point_domain(
        start=datetime(2026, 7, 1, tzinfo=UTC),
        end=datetime(2026, 7, 11, 11, tzinfo=UTC),
        lon=13.41,
        lat=52.52,
    )
    outside_xy = snapped_point_domain(
        start=datetime(2026, 7, 12, tzinfo=UTC),
        end=datetime(2026, 7, 13, tzinfo=UTC),
        lon=13.41,
        lat=100.0,
    )
    assert footprint.matches(overlapping) is True
    assert footprint.matches(no_overlap) is False
    assert footprint.matches(outside_xy) is False


def test_grid_domain_mixed_z_enumeration() -> None:
    domain = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 1.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 2.0, 1.0, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 2, False
            ),
        }
    )
    assert len(domain) == 2
    points = list(domain.enumerate())
    assert points[0].cells[AxisName.Z] == Cell(0.0, Interval(0.0, 10.0))
    assert points[0].cells[AxisName.T].coordinate == datetime(2026, 7, 11, tzinfo=UTC)
    assert points[1].cells[AxisName.T].coordinate == datetime(2026, 7, 11, 1, tzinfo=UTC)


def test_footprint_matches_vantage_by_intersection() -> None:
    """Footprint.matches routes through requested.matches(declared) — vantage intersects Z."""
    footprint = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
            AxisName.T: ContinuousAxis(
                AxisName.T,
                Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 18, tzinfo=UTC)),
            ),
        }
    )
    request = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, Interval(0.0, 10.0)),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 12, tzinfo=UTC), timedelta(hours=1), 1, False
            ),
        }
    )
    assert footprint.matches(request) is True

    upper_air = FootprintDomain(
        axes={
            **footprint.axes,
            AxisName.Z: RegularAxis(AxisName.Z, 100.0, 1.0, 1, False),
        }
    )
    assert upper_air.matches(request) is False


def test_regular_axis_getitem_and_len() -> None:
    axis = RegularAxis(AxisName.X, 10.0, 0.5, 4, cellular=False)
    assert len(axis) == 4
    assert axis[0] == Cell(10.0, None)
    assert axis[1] == Cell(10.5, None)
    assert axis[3] == Cell(11.5, None)
    with pytest.raises(IndexError):
        _ = axis[4]
    with pytest.raises(IndexError):
        _ = axis[-1]

    cellular = RegularAxis(
        AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 3, True
    )
    assert cellular[0] == Cell(
        datetime(2026, 7, 11, tzinfo=UTC),
        Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 11, 1, tzinfo=UTC)),
    )
    assert cellular[2].bounds == Interval(
        datetime(2026, 7, 11, 2, tzinfo=UTC), datetime(2026, 7, 11, 3, tzinfo=UTC)
    )


def test_regular_axis_extent_is_tick_span() -> None:
    """Extent is the tick span — identical formula whether cellular or instant."""
    instants = RegularAxis(AxisName.X, 10.0, 0.5, 4, cellular=False)
    cellular = RegularAxis(AxisName.X, 10.0, 0.5, 4, cellular=True)
    expected = Interval(10.0, 11.5)  # anchor + (count-1)*step
    assert instants.extent == expected
    assert cellular.extent == expected

    time_axis = RegularAxis(
        AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 3, True
    )
    assert time_axis.extent == Interval(
        datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 11, 2, tzinfo=UTC)
    )


def test_regular_axis_rejects_invalid_count_and_step() -> None:
    with pytest.raises(ValueError, match="count"):
        RegularAxis(AxisName.X, 0.0, 1.0, 0, False)
    with pytest.raises(ValueError, match="step"):
        RegularAxis(AxisName.X, 0.0, 0.0, 1, False)
    with pytest.raises(ValueError, match="step"):
        RegularAxis(AxisName.X, 0.0, -1.0, 1, False)
    with pytest.raises(ValueError, match="step"):
        RegularAxis(AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(0), 1, False)


def _four_regular_axes() -> dict[AxisName, RegularAxis]:
    return {
        AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
        AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
        AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
        AxisName.T: RegularAxis(
            AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 1, False
        ),
    }


def test_regular_domain_requires_exactly_four_axes() -> None:
    GridDomain(axes=_four_regular_axes())  # ok

    missing_t = {n: a for n, a in _four_regular_axes().items() if n is not AxisName.T}
    with pytest.raises(ValueError, match="four axes"):
        GridDomain(axes=missing_t)

    mismatched = _four_regular_axes()
    mismatched[AxisName.X] = RegularAxis(AxisName.Y, 0.0, 1.0, 1, False)
    with pytest.raises(ValueError, match="name"):
        GridDomain(axes=mismatched)

    footprint_axes = {
        AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
        AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
        AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
        AxisName.T: ContinuousAxis(
            AxisName.T,
            Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 18, tzinfo=UTC)),
        ),
    }
    FootprintDomain(axes=footprint_axes)  # ok
    with pytest.raises(ValueError, match="four axes"):
        FootprintDomain(axes={AxisName.X: footprint_axes[AxisName.X]})


def test_regular_domain_enumeration_order() -> None:
    """X → Y → Z → T nesting, T fastest; positional round-trip; point-timeline is time order."""
    domain = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 2, False),
            AxisName.Y: RegularAxis(AxisName.Y, 10.0, 1.0, 2, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 3, False
            ),
        }
    )
    assert len(domain) == 2 * 2 * 1 * 3
    points = list(domain.enumerate())
    assert len(points) == 12
    assert all(domain[i] == points[i] for i in range(12))

    # First point: all zeros; T advances fastest within the first spatial cell.
    assert points[0].cells[AxisName.X].coordinate == 0.0
    assert points[0].cells[AxisName.Y].coordinate == 10.0
    assert points[0].cells[AxisName.T].coordinate == datetime(2026, 7, 11, tzinfo=UTC)
    assert points[1].cells[AxisName.T].coordinate == datetime(2026, 7, 11, 1, tzinfo=UTC)
    assert points[2].cells[AxisName.T].coordinate == datetime(2026, 7, 11, 2, tzinfo=UTC)
    # After exhausting T, Y advances (Z count=1), then X.
    assert points[3].cells[AxisName.Y].coordinate == 11.0
    assert points[3].cells[AxisName.T].coordinate == datetime(2026, 7, 11, tzinfo=UTC)
    assert points[6].cells[AxisName.X].coordinate == 1.0

    # Degenerate point-timeline: count-1 spatial/Z → enumerates in time order.
    timeline = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 1.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 2.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 4, False
            ),
        }
    )
    assert [p.cells[AxisName.T].coordinate for p in timeline.enumerate()] == [
        datetime(2026, 7, 11, h, tzinfo=UTC) for h in range(4)
    ]


def test_footprint_domain_matches_by_extent() -> None:
    from meteoscape.clock import StoppedClock
    from meteoscape.manifold.cadence import CadenceDef, RollingAxis

    clock = StoppedClock(datetime(2026, 7, 11, 12, 0, tzinfo=UTC))
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(0),
        max_lead=timedelta(hours=6),
    )
    # A = 12:00, window_time = [12:00, 18:00]
    footprint = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-10.0, 10.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-5.0, 5.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: RollingAxis(AxisName.T, cadence, clock, timedelta(hours=1)),
        }
    )

    inside = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 12, tzinfo=UTC), timedelta(hours=1), 3, False
            ),
        }
    )
    assert footprint.matches(inside) is True

    # One tick past A + max_lead — T extent upper is 18:00; a tick at 19:00 is outside.
    past = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 19, tzinfo=UTC), timedelta(hours=1), 1, False
            ),
        }
    )
    assert footprint.matches(past) is False

    # Before A.
    before = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 11, tzinfo=UTC), timedelta(hours=1), 1, False
            ),
        }
    )
    assert footprint.matches(before) is False

    class _NonSeparable(Domain):
        def matches(self, other: Domain) -> bool:
            return False

        def intersect(self, other: Domain) -> Domain:
            return self

    assert footprint.matches(_NonSeparable()) is False


def test_grid_domain_matches_by_extent() -> None:
    outer = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 5, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 5, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 10, False
            ),
        }
    )
    # Enumerable ⊆ enumerable by span (tick alignment is not contains' job).
    inner = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 1.0, 1.0, 2, False),
            AxisName.Y: RegularAxis(AxisName.Y, 2.0, 1.0, 2, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, 2, tzinfo=UTC), timedelta(hours=1), 3, False
            ),
        }
    )
    assert outer.matches(inner) is True

    # Continuous other — per-axis span check.
    continuous = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(0.0, 4.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(0.0, 4.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(
                AxisName.T,
                Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 11, 9, tzinfo=UTC)),
            ),
        }
    )
    assert outer.matches(continuous) is True

    off_span = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 10.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), 1, False
            ),
        }
    )
    assert outer.matches(off_span) is False


# --- Hypothesis properties ---


@given(
    nx=st.integers(1, 3),
    ny=st.integers(1, 3),
    nz=st.integers(1, 2),
    nt=st.integers(1, 4),
)
def test_enumeration_round_trip_property(nx: int, ny: int, nz: int, nt: int) -> None:
    domain = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, nx, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, ny, False),
            AxisName.Z: RegularAxis(AxisName.Z, 0.0, 1.0, nz, False),
            AxisName.T: RegularAxis(
                AxisName.T, datetime(2026, 7, 11, tzinfo=UTC), timedelta(hours=1), nt, False
            ),
        }
    )
    points = list(domain.enumerate())
    assert len(points) == len(domain)
    assert all(domain[i] == points[i] for i in range(len(domain)))


@given(tick=st.integers(0, 5), noise=st.floats(-2e-9, 2e-9, allow_nan=False, allow_infinity=False))
def test_float_alignment_tolerance_property(tick: int, noise: float) -> None:
    """Within ~half tolerance succeeds; beyond 2x fails. Boundary is float-fuzzy — leave a gap."""
    outer = RegularAxis(AxisName.X, 0.0, 1.0, 8, False)
    inner = RegularAxis(AxisName.X, float(tick) + noise, 1.0, 2, False)
    offset = sub_lattice_offset(outer, inner)
    if abs(noise) <= LATTICE_TOLERANCE * 0.5:
        assert offset == tick
    elif abs(noise) >= LATTICE_TOLERANCE * 2:
        assert offset is None


# --- Extent-containment predicates (the moved reach geometry, ADR-0007) ---


def _footprint(*, x: Interval[float], days: int = 10) -> FootprintDomain:
    """Separable footprint: custom X extent, fixed Y/Z, T spanning `days` from a common anchor."""
    t0 = datetime(2026, 7, 11, 12, tzinfo=UTC)
    return FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, x),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(t0, t0 + timedelta(days=days))),
        }
    )


class _Curvilinear(Domain):
    """A non-separable stand-in: satisfies `Domain`, exposes no axes (concern #12, source role)."""

    def matches(self, other: Domain) -> bool:
        return False

    def intersect(self, other: Domain) -> Domain:
        return self


def test_contains_extents_is_whole_box_not_matches() -> None:
    outer = _footprint(x=Interval(-180.0, 180.0), days=16)
    inner = _footprint(x=Interval(-10.0, 40.0), days=10)
    assert contains_extents(outer, inner) is True
    assert contains_extents(inner, outer) is False
    # Equal extents nest both ways — the tie the reconciler resolves either direction.
    twin = _footprint(x=Interval(-180.0, 180.0), days=16)
    assert contains_extents(outer, twin) is True
    assert contains_extents(twin, outer) is True


def test_first_incomparable_returns_witness_then_none_for_a_chain() -> None:
    west = _footprint(x=Interval(-20.0, -10.0))
    east = _footprint(x=Interval(10.0, 20.0))
    witness = first_incomparable([("west", west), ("east", east)])
    assert witness is not None
    (left_key, _left), (right_key, _right) = witness
    assert {left_key, right_key} == {"west", "east"}

    # A nested chain has a maximum, so no pair fails to nest.
    big = _footprint(x=Interval(-180.0, 180.0), days=16)
    small = _footprint(x=Interval(-10.0, 40.0), days=10)
    assert first_incomparable([("big", big), ("small", small)]) is None


def test_split_extents_names_both_directions() -> None:
    """`Global x 10 d` vs `Europe x 16 d`: global wins x, europe wins t — report both."""
    glob = _footprint(x=Interval(-180.0, 180.0), days=10)
    europe = _footprint(x=Interval(-10.0, 40.0), days=16)
    message = split_extents("global", glob, "europe", europe)
    assert "global extends beyond europe on x" in message
    assert "europe extends beyond global on t" in message


def test_as_separable_returns_the_domain_or_none() -> None:
    footprint = _footprint(x=Interval(-10.0, 10.0))
    assert as_separable(footprint) is footprint  # same object, no synthesis
    assert as_separable(_Curvilinear()) is None
