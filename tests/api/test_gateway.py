"""Gateway resolve returns a Coverage (runtime-checked)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from fakes import point_timeline_domain
from meteoscape.api.gateway import Gateway
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
