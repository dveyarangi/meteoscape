"""Gateway resolve pass-through."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from meteoscape.api.gateway import Gateway
from meteoscape.manifold.core import Manifold, Selection
from meteoscape.manifold.domain import AxisName, ContinuousAxis, FootprintDomain, Interval
from meteoscape.parameters import AIR_TEMPERATURE


class _RecordingView:
    def __init__(self) -> None:
        self.calls: list[Selection] = []

    async def project(self, selection: Selection) -> Manifold:
        self.calls.append(selection)
        return self

    @property
    def capability(self):
        raise NotImplementedError


def test_gateway_resolve_forwards_to_best_view() -> None:
    view = _RecordingView()
    gateway = Gateway(view)
    selection = Selection(
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
    result = asyncio.run(gateway.resolve(selection))
    assert result is view
    assert view.calls == [selection]
