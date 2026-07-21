"""Profile reach — GridReachRule, resolve_reach, validate_calculators (RFC 0003)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import pytest

from fakes import SAMPLE_STORE, FakeProvider, core_parameters, footprint_domain
from meteoscape.config import ArbiterPolicy, StoreSpec
from meteoscape.identity import CalculatorKey, SourceKey
from meteoscape.manifold.cadence import CadenceDef, RollingAxis
from meteoscape.manifold.capability import FootprintCapability
from meteoscape.manifold.domain import (
    AXIS_ORDER,
    AxisName,
    ContinuousAxis,
    FootprintDomain,
    Interval,
)
from meteoscape.nodes.calculators.wind import wind_from_uv
from meteoscape.nodes.catalog.calculators import CalculatorManifest
from meteoscape.nodes.composition import (
    CalculatorRegistry,
    CompositionError,
    ProfileDef,
    RegisteredCalculator,
    RegisteredSource,
    SourceRegistry,
)
from meteoscape.nodes.reach import GridReachRule, resolve_reach, validate_calculators
from meteoscape.parameters import (
    AIR_TEMPERATURE,
    PRECIPITATION,
    WIND_DIRECTION,
    WIND_SPEED,
    WIND_U,
    WIND_V,
    ParameterId,
)

_T0 = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)


class _AdvancingClock:
    """Mutable clock for liveness — advance `instant` and RollingAxis extents move."""

    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant


def _global(*, days: int) -> FootprintDomain:
    """Global X/Y footprint with a static T span of `days` (004-shaped, no RollingAxis)."""
    return FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(_T0, _T0 + timedelta(days=days))),
        }
    )


def _box(*, x: Interval[float], days: int = 10) -> FootprintDomain:
    """Same Y/Z/T; custom X — for incomparable (non-nested) spatial extents."""
    return FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, x),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
            AxisName.T: ContinuousAxis(AxisName.T, Interval(_T0, _T0 + timedelta(days=days))),
        }
    )


def _key(dataset: str) -> SourceKey:
    return SourceKey(provider="test", dataset=dataset)


def _source(
    dataset: str,
    domain: FootprintDomain,
    *,
    priority: int,
    parameters: frozenset[ParameterId] | None = None,
) -> tuple[SourceKey, RegisteredSource]:
    key = _key(dataset)
    pids = parameters or frozenset({AIR_TEMPERATURE})
    table = core_parameters()
    capability = FootprintCapability(footprints={pid: (table.get(pid), domain) for pid in pids})
    return key, RegisteredSource(
        provider=FakeProvider(source_key=key, capability=capability),
        priority=priority,
        store=SAMPLE_STORE,
    )


def _source_per_param(
    dataset: str,
    domains: Mapping[ParameterId, FootprintDomain],
    *,
    priority: int = 0,
) -> tuple[SourceKey, RegisteredSource]:
    key = _key(dataset)
    table = core_parameters()
    capability = FootprintCapability(
        footprints={pid: (table.get(pid), domain) for pid, domain in domains.items()}
    )
    return key, RegisteredSource(
        provider=FakeProvider(source_key=key, capability=capability),
        priority=priority,
        store=SAMPLE_STORE,
    )


def _profile(
    sources: dict[SourceKey, RegisteredSource],
    calculators: CalculatorRegistry | None = None,
) -> ProfileDef:
    return ProfileDef(
        sources=SourceRegistry(sources=sources),
        calculators=calculators or CalculatorRegistry(calculators={}),
        root_store=StoreSpec(spatial_step=0.1, retention_interval=timedelta(days=14)),
        arbiter=ArbiterPolicy(),
    )


def _wind_calculator(*, inputs: frozenset[ParameterId] | None = None) -> CalculatorRegistry:
    parameters = core_parameters()
    key = CalculatorKey(method="wind_uv", name="default")
    return CalculatorRegistry(
        calculators={
            key: RegisteredCalculator(
                key=key,
                outputs={
                    WIND_SPEED: parameters.get(WIND_SPEED),
                    WIND_DIRECTION: parameters.get(WIND_DIRECTION),
                },
                inputs=inputs or frozenset({WIND_U, WIND_V}),
                manifest=CalculatorManifest(fn_id="wind_uv", fn=wind_from_uv),
                priority=0,
            )
        }
    )


def test_reach_single_candidate_returns_itself() -> None:
    domain = _global(days=10)
    assert GridReachRule().reach([(_key("a"), domain)]) is domain


def test_reach_equal_extent_tie_returns_one_of_the_inputs() -> None:
    left = _global(days=10)
    right = _global(days=10)
    assert left is not right
    for name in AXIS_ORDER:
        assert left.axis(name).extent == right.axis(name).extent
    winner = GridReachRule().reach([(_key("a"), left), (_key("b"), right)])
    assert winner is left or winner is right


def test_reach_longer_global_contains_shorter() -> None:
    long = _global(days=16)
    short = _global(days=10)
    assert GridReachRule().reach([(_key("short"), short), (_key("long"), long)]) is long


def test_reach_longest_among_three_globals() -> None:
    d16 = _global(days=16)
    d10 = _global(days=10)
    d5 = _global(days=5)
    assert GridReachRule().reach([(_key("a"), d16), (_key("b"), d10), (_key("c"), d5)]) is d16


def test_reach_incomparable_raises_naming_keys_axis_and_unbuilt_preference() -> None:
    west = _box(x=Interval(-20.0, -10.0))
    east = _box(x=Interval(10.0, 20.0))
    with pytest.raises(CompositionError, match=r"unbuilt") as exc:
        GridReachRule().reach([(_key("west"), west), (_key("east"), east)])
    message = str(exc.value)
    assert "west" in message and "east" in message
    assert "x" in message.lower()


def test_reach_incomparable_names_both_failing_axes_not_just_the_first() -> None:
    """`Global x 10 d` vs `Europe x 16 d` splits: global wins x, europe wins t — report both.

    Naming only the first axis whose extents differ points at `x`, where global *dominates*.
    """
    glob = _box(x=Interval(-180.0, 180.0), days=10)
    europe = _box(x=Interval(-10.0, 40.0), days=16)
    with pytest.raises(CompositionError) as exc:
        GridReachRule().reach([(_key("global"), glob), (_key("europe"), europe)])
    message = str(exc.value)
    assert "test:global extends beyond test:europe on x" in message
    assert "test:europe extends beyond test:global on t" in message


def test_resolve_reach_sources_picks_containing_footprint() -> None:
    short = _global(days=10)
    long = _global(days=16)
    k_short, s_short = _source("short", short, priority=1)
    k_long, s_long = _source("long", long, priority=2)
    result = resolve_reach(_profile({k_short: s_short, k_long: s_long}))
    assert result[AIR_TEMPERATURE] is long


@pytest.mark.parametrize("primary_priority,fallback_priority", [(1, 2), (2, 1)])
def test_resolve_reach_ignores_priority(primary_priority: int, fallback_priority: int) -> None:
    """The widest footprint wins whichever way priority runs — `grid` never consults it (004 shape)."""
    narrow = _global(days=10)
    wide = _global(days=16)
    k_primary, s_primary = _source("primary", narrow, priority=primary_priority)
    k_fallback, s_fallback = _source("fallback", wide, priority=fallback_priority)
    result = resolve_reach(_profile({k_primary: s_primary, k_fallback: s_fallback}))
    assert result[AIR_TEMPERATURE] is wide


def test_resolve_reach_omits_unserved_parameter() -> None:
    domain = _global(days=10)
    key, source = _source("only-temp", domain, priority=0)
    result = resolve_reach(_profile({key: source}))
    assert AIR_TEMPERATURE in result
    assert PRECIPITATION not in result


def test_validate_calculators_passes_when_inputs_served() -> None:
    domain = _global(days=10)
    key, source = _source("uv", domain, priority=0, parameters=frozenset({WIND_U, WIND_V}))
    validate_calculators(_profile({key: source}, _wind_calculator()))


def test_validate_calculators_raises_on_unserved_input() -> None:
    domain = _global(days=10)
    key, source = _source("temp-only", domain, priority=0)  # AIR_TEMPERATURE only
    with pytest.raises(CompositionError, match=r"wind_u") as exc:
        validate_calculators(_profile({key: source}, _wind_calculator()))
    assert "wind_uv" in str(exc.value)


def test_validate_calculators_raises_on_cycle() -> None:
    parameters = core_parameters()
    a = CalculatorKey(method="a", name="default")
    b = CalculatorKey(method="b", name="default")
    calcs = CalculatorRegistry(
        calculators={
            a: RegisteredCalculator(
                key=a,
                outputs={WIND_SPEED: parameters.get(WIND_SPEED)},
                inputs=frozenset({WIND_DIRECTION}),
                manifest=CalculatorManifest(fn_id="a", fn=wind_from_uv),
                priority=0,
            ),
            b: RegisteredCalculator(
                key=b,
                outputs={WIND_DIRECTION: parameters.get(WIND_DIRECTION)},
                inputs=frozenset({WIND_SPEED}),
                manifest=CalculatorManifest(fn_id="b", fn=wind_from_uv),
                priority=0,
            ),
        }
    )
    domain = _global(days=10)
    key, source = _source("temp", domain, priority=0)
    with pytest.raises(CompositionError, match="cycle") as exc:
        validate_calculators(_profile({key: source}, calcs))
    # Names the cycle, not one arbitrary participant.
    assert str(exc.value).count("->") == 2
    assert "a:default" in str(exc.value) and "b:default" in str(exc.value)


def test_validate_calculators_catches_cycle_a_source_also_serves() -> None:
    """A source serving the looped parameter must not hide the cycle from the guard.

    The Weaver scopes each input Arbiter over *every* producer of that input, so the graph is
    unbuildable regardless; letting it through here also recurses forever in `resolve_reach`.
    """
    parameters = core_parameters()
    a = CalculatorKey(method="a", name="default")
    b = CalculatorKey(method="b", name="default")
    calcs = CalculatorRegistry(
        calculators={
            a: RegisteredCalculator(
                key=a,
                outputs={WIND_SPEED: parameters.get(WIND_SPEED)},
                inputs=frozenset({WIND_DIRECTION}),
                manifest=CalculatorManifest(fn_id="a", fn=wind_from_uv),
                priority=0,
            ),
            b: RegisteredCalculator(
                key=b,
                outputs={WIND_DIRECTION: parameters.get(WIND_DIRECTION)},
                inputs=frozenset({WIND_SPEED}),
                manifest=CalculatorManifest(fn_id="b", fn=wind_from_uv),
                priority=0,
            ),
        }
    )
    # The source serves *both* looped parameters — the case that used to short-circuit the walk.
    key, source = _source_per_param(
        "both", {WIND_SPEED: _global(days=10), WIND_DIRECTION: _global(days=10)}
    )
    with pytest.raises(CompositionError, match="cycle"):
        validate_calculators(_profile({key: source}, calcs))


def test_resolve_reach_calculator_competes_with_a_source_at_the_top_level() -> None:
    """A Calculator is just another candidate at the Arbiter site — widest still wins."""
    uv = _global(days=16)
    direct = _global(days=10)
    k_uv, s_uv = _source_per_param("uv", {WIND_U: uv, WIND_V: uv})
    k_direct, s_direct = _source_per_param("direct", {WIND_SPEED: direct})
    profile = _profile({k_uv: s_uv, k_direct: s_direct}, _wind_calculator())
    validate_calculators(profile)
    # The calculator's 16 d footprint contains the source's 10 d one, so it wins on containment.
    assert resolve_reach(profile)[WIND_SPEED] is uv


def test_resolve_reach_ignores_the_stored_flag() -> None:
    """`stored` is a materialization knob; reach never consults it."""
    domain = _global(days=10)
    key, source = _source("uv", domain, priority=0, parameters=frozenset({WIND_U, WIND_V}))
    plain = _wind_calculator()
    stored = CalculatorRegistry(
        calculators={
            k: RegisteredCalculator(
                key=reg.key,
                outputs=reg.outputs,
                inputs=reg.inputs,
                manifest=reg.manifest,
                priority=reg.priority,
                stored=True,
            )
            for k, reg in plain.calculators.items()
        }
    )
    assert (
        resolve_reach(_profile({key: source}, stored))[WIND_SPEED]
        is resolve_reach(_profile({key: source}, plain))[WIND_SPEED]
    )


def test_resolve_reach_wind_identity_is_one_of_uv_footprints() -> None:
    u_domain = _global(days=10)
    v_domain = _global(days=10)
    assert u_domain is not v_domain
    key, source = _source_per_param("uv", {WIND_U: u_domain, WIND_V: v_domain})
    profile = _profile({key: source}, _wind_calculator())
    validate_calculators(profile)
    result = resolve_reach(profile)
    assert result[WIND_SPEED] is u_domain or result[WIND_SPEED] is v_domain
    assert result[WIND_DIRECTION] is result[WIND_SPEED]  # memoized calculator footprint


def test_resolve_reach_calculator_takes_contained_input() -> None:
    short = _global(days=10)
    long = _global(days=16)
    key, source = _source_per_param("uv", {WIND_U: short, WIND_V: long})
    profile = _profile({key: source}, _wind_calculator())
    validate_calculators(profile)
    assert resolve_reach(profile)[WIND_SPEED] is short


def test_resolve_reach_sheared_calculator_inputs_raise() -> None:
    west = _box(x=Interval(-20.0, -10.0))
    east = _box(x=Interval(10.0, 20.0))
    key, source = _source_per_param("uv", {WIND_U: west, WIND_V: east})
    profile = _profile({key: source}, _wind_calculator())
    validate_calculators(profile)
    with pytest.raises(CompositionError, match=r"shear|wind_u|wind_v"):
        resolve_reach(profile)


def test_resolve_reach_rolling_axis_stays_live() -> None:
    clock = _AdvancingClock(_T0)
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(0),
        max_lead=timedelta(days=7),
    )
    domain = footprint_domain(clock, cadence=cadence)
    assert isinstance(domain.axis(AxisName.T), RollingAxis)
    key, source = _source("live", domain, priority=0)
    profile = _profile({key: source})
    reach_map = resolve_reach(profile)
    before = reach_map[AIR_TEMPERATURE].axis(AxisName.T).extent.upper
    clock.instant = _T0 + timedelta(days=1)
    after = reach_map[AIR_TEMPERATURE].axis(AxisName.T).extent.upper
    assert after == before + timedelta(days=1)
