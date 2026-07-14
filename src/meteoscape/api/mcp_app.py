"""MCP surface adapter: protocol ↔ canonical — the first surface.

Builds the FastMCP app and registers `forecast_hourly`. Translates a call into a canonical
`Selection`, drives the Gateway, and serializes the returned Coverage (serialize only).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ..clock import Clock, floor_to
from ..errors import BadRequest, CapabilityMismatch, RuntimeFailure
from ..manifold.core import Coverage, Selection
from ..manifold.domain import (
    AxisName,
    EnumerableAxis,
    GridDomain,
    Interval,
    RegularAxis,
    VantageAxis,
)
from ..manifold.provenance import AtomicOrigin
from ..nodes.catalog.paramtable import ParameterTable, StaticParameterTable
from ..parameters import (
    AIR_TEMPERATURE,
    CLOUD_COVER,
    PRECIPITATION,
    RELATIVE_HUMIDITY,
    WIND_DIRECTION,
    WIND_SPEED,
    ParameterId,
)
from .gateway import Gateway

_HOUR = timedelta(hours=1)
_SPATIAL_STEP = 1.0
# Edge-authored near-surface observation aperture (session 0011 / ticket 002).
_VANTAGE_Z = Interval(0.0, 10.0)

# Surface menu: requestable names. Presence here ⇔ requestable (not a ParameterDef flag).
# `wind_u` / `wind_v` have no entry. Speed/direction stay in the table so 002b reveals them via
# exposure ∩ capability once Calculators weave them in.
_EXPOSURE: frozenset[ParameterId] = frozenset(
    {
        AIR_TEMPERATURE,
        PRECIPITATION,
        RELATIVE_HUMIDITY,
        CLOUD_COVER,
        WIND_SPEED,
        WIND_DIRECTION,
    }
)


def build_mcp_app(
    gateway: Gateway,
    clock: Clock,
    default_horizon: timedelta,
    *,
    parameters: ParameterTable | None = None,
) -> FastMCP:
    """Construct the MCP app with `forecast_hourly` registered against a woven Gateway."""
    table = parameters or StaticParameterTable.core()
    envelope = gateway.best_view.capability.parameters
    hour_count = _horizon_hours(default_horizon)
    menu = _exposed_menu(envelope)
    served = ", ".join(sorted(menu)) or "(none)"

    mcp: FastMCP = FastMCP("meteoscape")
    description = (
        "Hourly point forecast for a latitude/longitude. "
        f"Served parameters: {served}. "
        f"Default window: {hour_count} hourly ticks from floor(now, 1h) UTC. "
        "Optional `parameters` selects a subset (default: all served). "
        "Optional `start`/`end` are reserved until request shaping lands."
    )

    @mcp.tool(description=description)
    async def forecast_hourly(
        latitude: float,
        longitude: float,
        parameters: list[str] | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, object]:
        try:
            selection = build_selection(
                latitude=latitude,
                longitude=longitude,
                parameter_names=parameters,
                start=start,
                end=end,
                clock=clock,
                default_horizon=default_horizon,
                envelope=envelope,
                table=table,
            )
            coverage = await gateway.resolve(selection)
            return serialize_coverage(coverage)
        except BadRequest as exc:
            raise ToolError(f"bad-request: {exc}") from exc
        except CapabilityMismatch as exc:
            raise ToolError(f"capability-mismatch: {exc}") from exc
        except RuntimeFailure as exc:
            raise ToolError(f"runtime-failure: {exc}") from exc

    return mcp


def build_selection(
    *,
    latitude: float,
    longitude: float,
    parameter_names: Sequence[str] | None,
    start: str | None,
    end: str | None,
    clock: Clock,
    default_horizon: timedelta,
    envelope: Mapping[ParameterId, object],
    table: ParameterTable,
) -> Selection:
    """Wire lat/lon (+ optional parameter names) into the v1 request Selection."""
    if not -90.0 <= latitude <= 90.0:
        raise BadRequest(f"latitude out of range: {latitude}")
    if not -180.0 <= longitude <= 180.0:
        raise BadRequest(f"longitude out of range: {longitude}")
    if start is not None or end is not None:
        raise BadRequest("start/end not yet supported")

    params = _resolve_parameters(parameter_names, envelope=envelope, table=table)
    hours = _horizon_hours(default_horizon)
    anchor = floor_to(clock.now(), _HOUR)
    domain = GridDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, longitude, _SPATIAL_STEP, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, latitude, _SPATIAL_STEP, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, _VANTAGE_Z),
            AxisName.T: RegularAxis(AxisName.T, anchor, _HOUR, hours, True),
        }
    )
    return Selection(domain=domain, parameters=params)


def serialize_coverage(coverage: Coverage) -> dict[str, object]:
    """Compact agent JSON: shared `valid_time` + per-parameter `{unit, values, provenance}`."""
    domain = coverage.domain
    if not isinstance(domain, GridDomain):
        raise TypeError("Coverage domain must be a GridDomain")
    t_axis = domain.axis(AxisName.T)
    if not isinstance(t_axis, EnumerableAxis):
        raise TypeError("Coverage T axis must be enumerable")
    payload: dict[str, object] = {
        "valid_time": [_iso_z(t_axis[i].coordinate) for i in range(len(t_axis))],
    }
    for pid, definition in coverage.capability.parameters.items():
        data = coverage.ranges[pid]
        values: list[float | None] = []
        for i, value in enumerate(data.values):
            if data.present is not None and not data.present[i]:
                values.append(None)
            else:
                values.append(float(value))
        provenance = coverage.provenance.summary(pid)
        origin = provenance.origin
        if not isinstance(origin, AtomicOrigin):
            raise TypeError(f"unsupported origin type for {pid}: {type(origin).__name__}")
        payload[str(pid)] = {
            "unit": str(definition.canonical_unit),
            "values": values,
            "provenance": {
                "source": str(origin.source),
                "exp": _iso_z(provenance.expiration),
            },
        }
    return payload


def _exposed_menu(envelope: Mapping[ParameterId, object]) -> frozenset[ParameterId]:
    """Requestable ∩ woven capability — the surface menu and default parameter set."""
    return frozenset(pid for pid in envelope if pid in _EXPOSURE)


def _resolve_parameters(
    names: Sequence[str] | None,
    *,
    envelope: Mapping[ParameterId, object],
    table: ParameterTable,
) -> frozenset[ParameterId]:
    menu = _exposed_menu(envelope)
    if names is None:
        return menu
    resolved: list[ParameterId] = []
    for name in names:
        pid = ParameterId(name)
        if pid not in table:
            raise BadRequest(f"unknown parameter {name!r}")
        if pid not in _EXPOSURE:
            raise BadRequest(f"parameter {name!r} is not requestable")
        if pid not in envelope:
            raise BadRequest(f"parameter {name!r} is not served by this profile")
        resolved.append(pid)
    return frozenset(resolved)


def _horizon_hours(horizon: timedelta) -> int:
    hours = horizon / _HOUR
    if hours != int(hours) or int(hours) < 1:
        raise ValueError(f"default_horizon must be a positive whole number of hours, got {horizon}")
    return int(hours)


def _iso_z(moment: object) -> str:
    if not isinstance(moment, datetime):
        raise TypeError(f"expected datetime, got {type(moment).__name__}")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
