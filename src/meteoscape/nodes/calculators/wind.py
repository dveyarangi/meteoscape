"""Wind calculator plugin — `{wind_speed, wind_direction}` from `{wind_u, wind_v}`."""

from __future__ import annotations

import math
from collections.abc import Mapping

from ...manifold.core import Coverage
from ...manifold.data import ParameterData, and_present
from ...manifold.domain import EnumerableDomain
from ...parameters import WIND_DIRECTION, WIND_SPEED, WIND_U, WIND_V, ParameterId
from ..catalog.calculators import CalculatorManifest


def wind_from_uv(
    cov: Coverage,
) -> tuple[EnumerableDomain, Mapping[ParameterId, ParameterData]]:
    """`speed = hypot(u, v)`; meteorological FROM-direction via `atan2(-u, -v)` (inverse of OM encode)."""
    u, v = cov.ranges[WIND_U], cov.ranges[WIND_V]
    present = and_present(u.present, v.present, n=len(cov.domain))
    speed = [math.hypot(a, b) for a, b in zip(u.values, v.values, strict=True)]
    direction = [
        math.degrees(math.atan2(-a, -b)) % 360.0 for a, b in zip(u.values, v.values, strict=True)
    ]
    return cov.domain, {
        WIND_SPEED: ParameterData(values=speed, present=present),
        WIND_DIRECTION: ParameterData(values=direction, present=present),
    }


MANIFEST = CalculatorManifest(fn_id="wind_uv", fn=wind_from_uv)
