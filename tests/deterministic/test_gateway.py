"""Gateway resolve returns a Coverage (runtime-checked), and release lets a composition go."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from fakes import point_timeline_domain
from meteoscape.gateway import Closeable, Gateway
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import EnumerableCapability
from meteoscape.manifold.core import Coverage, Manifold, Selection
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.domain import AxisName, ContinuousAxis, FootprintDomain, Interval
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.parameters import AIR_TEMPERATURE


def _coverage() -> CoverageRecord:
    domain = point_timeline_domain(hours=1)
    table = StaticParameterTable.core()
    return CoverageRecord(
        capability=EnumerableCapability(
            domain=domain,
            parameters={AIR_TEMPERATURE: table.get(AIR_TEMPERATURE)},
        ),
        ranges={AIR_TEMPERATURE: ParameterData(values=[1.0], present=None)},
        provenance=Uniform(
            Provenance(
                origin=AtomicOrigin(
                    SourceKey("fake", "default"),
                    datetime(2026, 7, 11, tzinfo=UTC),
                ),
                fetched_at=datetime(2026, 7, 11, 12, tzinfo=UTC),
                expiration=datetime(2026, 7, 11, 13, tzinfo=UTC),
            )
        ),
    )


class _CoverageView:
    def __init__(self, result: Coverage) -> None:
        self.calls: list[Selection] = []
        self._result = result

    async def project(self, selection: Selection) -> Manifold:
        self.calls.append(selection)
        return self._result

    @property
    def capability(self):
        raise NotImplementedError


class _NonCoverageView:
    async def project(self, selection: Selection) -> Manifold:
        return self

    @property
    def capability(self):
        raise NotImplementedError


def _selection() -> Selection:
    return Selection(
        domain=FootprintDomain(
            axes={
                AxisName.X: ContinuousAxis(AxisName.X, Interval(0.0, 1.0)),
                AxisName.Y: ContinuousAxis(AxisName.Y, Interval(0.0, 1.0)),
                AxisName.Z: ContinuousAxis(AxisName.Z, Interval(0.0, 0.0)),
                AxisName.T: ContinuousAxis(
                    AxisName.T,
                    Interval(datetime(2026, 7, 11, tzinfo=UTC), datetime(2026, 7, 12, tzinfo=UTC)),
                ),
            }
        ),
        parameters=frozenset({AIR_TEMPERATURE}),
    )


class _RecordingCloseable:
    """A `Closeable` logging its own release into a log shared with its siblings.

    One shared log rather than a flag each: release *order* is the promise under test, and
    independent flags cannot express it.
    """

    def __init__(self, name: str, log: list[str]) -> None:
        self._name = name
        self._log = log

    async def aclose(self) -> None:
        self._log.append(self._name)


def test_aclose_releases_what_the_composition_built() -> None:
    released: list[str] = []
    gateway = Gateway(_CoverageView(_coverage()), [_RecordingCloseable("store", released)])
    asyncio.run(gateway.aclose())
    assert released == ["store"]


def test_aclose_unwinds_in_reverse_of_construction() -> None:
    """Outermost-first: the root store is built last, so it is released first."""
    released: list[str] = []
    gateway = Gateway(
        _CoverageView(_coverage()),
        [_RecordingCloseable("provider", released), _RecordingCloseable("root store", released)],
    )
    asyncio.run(gateway.aclose())
    assert released == ["root store", "provider"]


def test_second_aclose_releases_nothing_again() -> None:
    """Idempotence is ours to keep: `Closeable` is structural, so nothing's own `aclose` can be
    required to tolerate being called twice."""
    released: list[str] = []
    gateway = Gateway(_CoverageView(_coverage()), [_RecordingCloseable("store", released)])

    async def close_twice() -> None:
        await gateway.aclose()
        await gateway.aclose()

    asyncio.run(close_twice())
    assert released == ["store"]


def test_composition_holding_nothing_closes() -> None:
    # Today's shipped shape: no producer or store holds anything, so this is the live path.
    asyncio.run(Gateway(_CoverageView(_coverage())).aclose())


def test_one_failed_release_does_not_strand_the_rest() -> None:
    released: list[str] = []

    class _FailingCloseable:
        async def aclose(self) -> None:
            raise OSError("connection reset while closing")

    gateway = Gateway(
        _CoverageView(_coverage()),
        [_RecordingCloseable("provider", released), _FailingCloseable()],
    )
    with pytest.raises(ExceptionGroup) as raised:
        asyncio.run(gateway.aclose())
    # The provider sits *before* the failing one, so reverse order reaches it only if the failure
    # was collected rather than propagated.
    assert released == ["provider"]
    assert [type(exc) for exc in raised.value.exceptions] == [OSError]


def test_defining_aclose_alone_declares_release() -> None:
    """Structural, so a future Store or Provider declares release by defining the method and
    importing nothing — the check that keeps lifetime out of the algebra."""
    assert isinstance(_RecordingCloseable("store", []), Closeable)
    assert not isinstance(_CoverageView(_coverage()), Closeable)


def test_what_holds_nothing_is_passed_over() -> None:
    """A caller hands over whole construction sites, most of whose members hold nothing — so a site
    must survive being mostly inert, and the survivors must keep their order across sites."""
    released: list[str] = []
    gateway = Gateway(
        _CoverageView(_coverage()),
        [_RecordingCloseable("provider", released), _CoverageView(_coverage())],
        [_RecordingCloseable("store", released)],
    )
    asyncio.run(gateway.aclose())
    assert released == ["store", "provider"]


def test_gateway_resolve_returns_coverage() -> None:
    coverage = _coverage()
    view = _CoverageView(coverage)
    gateway = Gateway(view)
    selection = _selection()
    result = asyncio.run(gateway.resolve(selection))
    assert result is coverage
    assert view.calls == [selection]


def test_gateway_resolve_rejects_non_coverage() -> None:
    gateway = Gateway(_NonCoverageView())
    with pytest.raises(TypeError, match="Coverage"):
        asyncio.run(gateway.resolve(_selection()))
