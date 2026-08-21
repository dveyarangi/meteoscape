"""MCP surface adapter: protocol ↔ canonical — the first surface.

Builds the FastMCP app and registers `forecast_hourly`. Translates a call into a canonical
`Selection`, drives the Gateway, and serializes the returned Coverage (serialize only). Also
registers the shutdown hook that releases the composition it was handed - a surface drives the
composition it receives, and it is the one that knows when the serving stops.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ..clock import Clock
from ..errors import BadRequest, CapabilityMismatch, RuntimeFailure
from ..gateway import Gateway
from ..manifold.capability import Capability
from ..manifold.core import Coverage, Selection
from ..manifold.domain import (
    AxisName,
    Coordinate,
    Domain,
    GridDomain,
    Interval,
    RegularAxis,
    SelectionDomain,
    SnappedAxis,
    VantageAxis,
    as_separable,
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

_HOUR = timedelta(hours=1)
_SPATIAL_STEP = 1.0
# Edge-authored near-surface observation aperture.
_VANTAGE_Z = Interval(0.0, 10.0)

# Surface menu: requestable names. Presence here ⇔ requestable (not a ParameterDef flag).
# `wind_u` / `wind_v` have no entry — they are inputs, not products. Speed/direction stay listed even
# when no Calculator is woven: the served menu is exposure ∩ capability, so they appear only once one is.
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
    *,
    parameters: ParameterTable | None = None,
) -> FastMCP:
    """Construct the MCP app with `forecast_hourly` registered against a woven Gateway."""
    table = parameters or StaticParameterTable.core()
    capability = gateway.best_view.capability
    menu = _exposed_menu(capability.parameters)
    served = ", ".join(sorted(menu)) or "(none)"

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
        """The composition lives exactly as long as the server serves.

        This hook is the only place teardown can run inside the server's own loop — after `run()`
        returns the loop is gone, and a client bound to it could no longer be closed. `_server` is
        FastMCP's callback contract, not ours: the manager calls the lifespan with the server. A
        teardown failure propagates uncaught: `aclose` is not the request path, the client has
        already disconnected, and the traceback as the process exits is the report.
        """
        try:
            yield
        finally:
            await gateway.aclose()

    mcp: FastMCP = FastMCP("meteoscape", lifespan=lifespan)
    description = (
        "Hourly point forecast for a latitude/longitude. "
        f"Served parameters: {served}. "
        f"{_horizon_sentence(capability, menu)}"
        "Optional `parameters` selects a subset (default: all served). "
        "Optional `start`/`end` bound the hourly window (ISO 8601 datetimes, UTC; naive times "
        "read as UTC; bare dates are not accepted — give e.g. 2026-07-20T00:00; `end` is "
        "inclusive; omit `start` to begin now; omit `end` to run to the full horizon; bounds "
        "outside the served range yield the servable part — the response's `valid_time` shows "
        "the window actually served)."
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
                capability=capability,
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
    capability: Capability,
    table: ParameterTable,
) -> Selection:
    """Author the canonical request: point X/Y, vantage Z, and a Snapped-T window of raw instants.

    The edge holds no tick arithmetic — the resolver's grid supplies anchor and step and fits the
    bounds (`ground`/`clip`, ADR-0002). `BadRequest` stays purely syntactic; whether a well-formed
    window is servable is admission's question, so the edge never rejects on reach's word.
    """
    if not -90.0 <= latitude <= 90.0:
        raise BadRequest(f"latitude out of range: {latitude}")
    if not -180.0 <= longitude <= 180.0:
        raise BadRequest(f"longitude out of range: {longitude}")

    params = _resolve_parameters(parameter_names, envelope=capability.parameters, table=table)
    if not params:
        # Reject before the reach fold, which is undefined over zero parameters.
        raise CapabilityMismatch("profile serves no parameters")

    start_i = _parse_bound(start) if start is not None else clock.now()
    if end is not None:
        end_i = _parse_bound(end)
        if start_i > end_i:
            raise BadRequest(
                f"start is after end ({start!r} > {end!r})"
                if start is not None
                else f"end {end!r} is before now"
            )
    else:
        # The folded reach end, read live — a hint resolution's intersection may trim, not a
        # promise. `min` over the requested parameters (never a sentinel): at the first
        # diverging-reach parameter set the fold is what keeps a mixed response one shape (#30).
        reach_end = min(_t_extent(capability.reach(p)).upper for p in params)
        # A start beyond reach authors the single-instant ask; admission answers the mismatch.
        end_i = max(reach_end, start_i)

    domain = SelectionDomain(
        axes={
            AxisName.X: RegularAxis(AxisName.X, longitude, _SPATIAL_STEP, 1, False),
            AxisName.Y: RegularAxis(AxisName.Y, latitude, _SPATIAL_STEP, 1, False),
            AxisName.Z: VantageAxis(AxisName.Z, _VANTAGE_Z),
            AxisName.T: SnappedAxis(AxisName.T, Interval(start_i, end_i)),
        }
    )
    return Selection(domain=domain, parameters=params)


def _parse_bound(raw: str) -> datetime:
    """One `start`/`end` string as an aware-UTC raw instant; naive reads as UTC.

    `date.fromisoformat` probes first because `datetime.fromisoformat` silently reads a bare date as
    midnight. Refusing bare and week dates prevents an accidental, silently shortened answer.
    """
    try:
        date.fromisoformat(raw)
    except ValueError:
        pass
    else:
        raise BadRequest(f"bare dates are not accepted; use a datetime like {raw}T00:00")
    try:
        instant = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise BadRequest(f"unparsable start/end: {raw!r}") from exc
    return instant.replace(tzinfo=UTC) if instant.tzinfo is None else instant.astimezone(UTC)


def _t_extent(reach: Domain) -> Interval[datetime]:
    """A reach's T extent, narrowed: the axis extent is coordinate-generic (cf. `_iso_z`)."""
    separable = as_separable(reach)
    if separable is None:
        raise TypeError(f"reach must be separable, got {type(reach).__name__}")
    extent = separable.axis(AxisName.T).extent
    lower, upper = extent.lower, extent.upper
    if not isinstance(lower, datetime) or not isinstance(upper, datetime):
        raise TypeError(f"expected a datetime extent, got {extent!r}")
    return Interval(lower, upper)


def _horizon_sentence(capability: Capability, menu: frozenset[ParameterId]) -> str:
    """The description's horizon sentence — empty when the menu is (nothing to narrate, and a
    `min` over zero reaches must not raise at startup).

    Narrated relatively ("out to N ahead of the latest run"), never as absolute instants: the
    description is built once and frozen for the process lifetime, and a `RollingAxis` extent
    length is invariant as its bounds move, which keeps the relative form true indefinitely.
    The `min` fold over the exposed menu mirrors `build_selection`'s reach-end fold, so the
    description promises no further than the narrowest served parameter reaches.
    """
    if not menu:
        return ""
    extents = (_t_extent(capability.reach(pid)) for pid in menu)
    horizon = min(extent.upper - extent.lower for extent in extents)
    hours = int(horizon // _HOUR)
    days = hours // 24
    span = f"{days} days" if days >= 1 else f"{hours} hours"
    return f"Horizon: out to {span} ahead of the latest model run. "


def serialize_coverage(coverage: Coverage) -> dict[str, object]:
    """Compact agent JSON: shared `valid_time` + per-parameter `{unit, values, provenance}`."""
    domain = coverage.domain
    if not isinstance(domain, GridDomain):
        raise TypeError("Coverage domain must be a GridDomain")
    t_axis = domain.axis(AxisName.T)
    payload: dict[str, object] = {
        "valid_time": [_iso_z(t_axis[i].coordinate) for i in range(len(t_axis))],
    }
    for pid, definition in coverage.capability.parameters.items():
        data = coverage.ranges[pid]
        values = [
            None if not data.is_present(i) else float(value) for i, value in enumerate(data.values)
        ]
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
    if names is not None and not names:
        # `None` means "all served"; an explicitly empty ask is meaningless.
        raise BadRequest("parameters must not be empty; omit it to get all served parameters")
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


def _iso_z(moment: Coordinate) -> str:
    # `Coordinate` is `float | datetime`; only the time axis serializes here.
    if not isinstance(moment, datetime):
        raise TypeError(f"expected datetime, got {type(moment).__name__}")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
