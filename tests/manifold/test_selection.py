"""Selection.with_params — parameter-set rewrite (ADR-0004)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from meteoscape.manifold.core import Selection
from meteoscape.manifold.domain import AxisName, GridDomain, RegularAxis
from meteoscape.parameters import AIR_TEMPERATURE, PRECIPITATION, WIND_U


def _point_domain() -> GridDomain:
    return GridDomain(
        {
            AxisName.X: RegularAxis(AxisName.X, 0.0, 1.0, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, 0.0, 1.0, 1, False),
            AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
            AxisName.T: RegularAxis(
                AxisName.T,
                datetime(2026, 7, 12, tzinfo=UTC),
                timedelta(hours=1),
                2,
                True,
            ),
        }
    )


def test_with_params_keeps_domain_and_rewrites_parameters() -> None:
    domain = _point_domain()
    selection = Selection(domain=domain, parameters=frozenset({AIR_TEMPERATURE, PRECIPITATION}))
    narrowed = selection.with_params(frozenset({AIR_TEMPERATURE}))
    assert narrowed.domain is domain
    assert narrowed.parameters == frozenset({AIR_TEMPERATURE})


def test_with_params_rejects_extras() -> None:
    selection = Selection(
        domain=_point_domain(),
        parameters=frozenset({AIR_TEMPERATURE}),
    )
    with pytest.raises(ValueError, match="not in"):
        selection.with_params(frozenset({AIR_TEMPERATURE, WIND_U}))
