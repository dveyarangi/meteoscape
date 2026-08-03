"""Shared native→canonical conversion edges.

Vendor quantities are converted before anything downstream sees a value, at the shape wrapper that
executes a producer's declared tap table ([parameters.md](../../../docs/parameters.md)). Both kinds of
edge live here — a scale factor, and a transform between quantities — because neither is vendor
knowledge: every vendor publishing wind as a speed and a bearing means the same thing by it. These are
the seed of a verified conversion catalogue; until it exists, each edge is hand-declared per tap.
"""

from __future__ import annotations

import math

KMH_TO_MS = 1.0 / 3.6


def kmh_to_ms(value: float) -> float:
    """Convert wind speed from km/h to canonical m/s."""
    return value * KMH_TO_MS


def u_component(speed_ms: float, direction_deg: float) -> float:
    """Eastward wind from speed and meteorological direction — degrees FROM which the wind blows.

    That convention is the whole content of the minus sign: a wind *from* the east (90°) blows
    westward, so its `u` is negative. `wind_from_uv` inverts this pair on the read side.
    """
    return -speed_ms * math.sin(math.radians(direction_deg))


def v_component(speed_ms: float, direction_deg: float) -> float:
    """Northward wind from speed and meteorological direction (see `u_component`)."""
    return -speed_ms * math.cos(math.radians(direction_deg))
