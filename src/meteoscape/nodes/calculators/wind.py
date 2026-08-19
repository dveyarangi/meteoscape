"""Wind calculator plugin — `{wind_speed, wind_direction}` from `{wind_u, wind_v}`."""

from __future__ import annotations

import math
from collections.abc import Mapping

from ...manifold.core import Coverage
from ...manifold.data import ParameterData, and_present
from ...manifold.domain import EnumerableDomain
from ...parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V, ParameterId
from ..catalog.calculators import CalculatorManifest

CALM_SPEED_FLOOR = 1e-9
"""m/s. Below this, u = v = ±0 and the reconstructed direction is `atan2` of signed zeros —
a numerically arbitrary angle (today: 180.0). An epsilon guard on the degenerate math,
deliberately not a meteorological calm convention (that would be product policy)."""


def wind_from_uv(
    cov: Coverage,
) -> tuple[EnumerableDomain, Mapping[ParameterId, ParameterData]]:
    """`speed = hypot(u, v)`; meteorological FROM-direction via `atan2(-u, -v)` (inverse of OM encode)."""
    u, v = cov.ranges[WIND_U], cov.ranges[WIND_V]
    n = len(cov.domain)
    present = and_present(u.present, v.present, n=n)
    speed = [math.hypot(a, b) for a, b in zip(u.values, v.values, strict=True)]
    direction = [
        math.degrees(math.atan2(-a, -b)) % 360.0 for a, b in zip(u.values, v.values, strict=True)
    ]
    base = present if present is not None else (True,) * n
    present_direction = [p and s > CALM_SPEED_FLOOR for p, s in zip(base, speed, strict=True)]
    return cov.domain, {
        WIND_SPEED: ParameterData(values=speed, present=present),
        WIND_DIRECTION: ParameterData.of(direction, present_direction),
    }


MANIFEST = CalculatorManifest(
    fn_id="wind_uv",
    fn=wind_from_uv,
    outputs=frozenset({WIND_SPEED, WIND_DIRECTION}),
    inputs=frozenset({WIND_U, WIND_V}),
)
