"""Open-Meteo vendor leaf — its `Probe`, its declarations, and the catalogue `MANIFEST`.

Serves the 6 canonical parameters as a point plus an hourly series, so it contributes a
`TimelineProbe` and a tap table to `RollingTimeline` and no algebra of its own: one query out, one
envelope parsed, everything geometric decided by what is declared here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

from ...clock import Clock
from ...config import StoreSpec
from ...errors import CompositionError, RuntimeFailure
from ...identity import SourceKey
from ...manifold.cadence import CadenceDef
from ...manifold.domain import Interval
from ...parameters import (
    AIR_TEMPERATURE,
    CLOUD_COVER,
    PRECIPITATION,
    RELATIVE_HUMIDITY,
    WIND_U,
    WIND_V,
    ParameterId,
)
from ..catalog.paramtable import ParameterTable
from ..catalog.providers import OfferingSpec, ProviderManifest
from .base import FetchRequest, HttpxTransport, Provider, Transport
from .normalization import u_component, v_component
from .timeline import (
    HOURLY_STEP,
    Z_2M,
    Z_10M,
    Z_COLUMN,
    Z_SURFACE,
    PointSeriesTap,
    RollingTimeline,
    TapTable,
    TimelineDelivery,
    VendorVar,
    passthrough,
    pointwise,
)

BASE_URL = "https://api.open-meteo.com"
IMPL_ID = "open-meteo"
PROVIDER_ID = "open-meteo"
BEST_MATCH = "best_match"

# The vendor serves 16 calendar days of hourly ticks: [today00, today00+15d23h].
CADENCE = CadenceDef(
    cadence=timedelta(hours=1),
    publication_latency=timedelta(hours=1),
    max_lead=timedelta(hours=383),
    shelf=timedelta(hours=24),  # midnight-anchored: the window turns once per calendar day
)

_CANONICAL_IDS: frozenset[ParameterId] = frozenset(
    {AIR_TEMPERATURE, RELATIVE_HUMIDITY, WIND_U, WIND_V, PRECIPITATION, CLOUD_COVER}
)

_wind_u = pointwise("wind_speed_10m", "wind_direction_10m", fn=u_component)
_wind_v = pointwise("wind_speed_10m", "wind_direction_10m", fn=v_component)

_WIND_VARS = (
    VendorVar("wind_speed_10m", "km/h"),
    VendorVar("wind_direction_10m", "°"),
)

TAPS = TapTable(
    (
        PointSeriesTap(
            produces=AIR_TEMPERATURE,
            vendor_vars=(VendorVar("temperature_2m", "°C"),),
            z=Z_2M,
            decode=passthrough("temperature_2m"),
        ),
        PointSeriesTap(
            produces=RELATIVE_HUMIDITY,
            vendor_vars=(VendorVar("relative_humidity_2m", "%"),),
            z=Z_2M,
            decode=passthrough("relative_humidity_2m"),
        ),
        PointSeriesTap(
            produces=WIND_U,
            vendor_vars=_WIND_VARS,
            z=Z_10M,
            decode=_wind_u,
        ),
        PointSeriesTap(
            produces=WIND_V,
            vendor_vars=_WIND_VARS,
            z=Z_10M,
            decode=_wind_v,
        ),
        PointSeriesTap(
            produces=PRECIPITATION,
            vendor_vars=(VendorVar("precipitation", "mm"),),
            z=Z_SURFACE,
            decode=passthrough("precipitation"),
        ),
        PointSeriesTap(
            produces=CLOUD_COVER,
            vendor_vars=(VendorVar("cloud_cover", "%"),),
            z=Z_COLUMN,
            decode=passthrough("cloud_cover"),
        ),
    )
)


class OpenMeteoProbe:
    """Open-Meteo's forecast endpoint: one query built, one envelope parsed, nothing interpreted.

    Both halves are vendor knowledge and nothing else — how this API spells a point and a span, and
    where it puts the series. It never sees the request, so it cannot decide what is servable.
    """

    reports_units = True
    """`hourly_units` is published on every response, so the wrapper checks it against the taps."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    async def retrieve(
        self,
        *,
        longitude: float,
        latitude: float,
        over: Interval[datetime],
        variables: Sequence[str],
    ) -> TimelineDelivery:
        raw = await self._transport.fetch(
            self._query(longitude=longitude, latitude=latitude, over=over, variables=variables)
        )
        return self._parse(raw, variables)

    def _query(
        self,
        *,
        longitude: float,
        latitude: float,
        over: Interval[datetime],
        variables: Sequence[str],
    ) -> FetchRequest:
        """The span as this vendor spells one: `start_hour` / `end_hour`, both inclusive, in UTC."""
        return FetchRequest(
            path="/v1/forecast",
            params={
                "latitude": _fmt_coord(latitude),
                "longitude": _fmt_coord(longitude),
                "hourly": ",".join(variables),
                "start_hour": _fmt_hour(over.lower),
                "end_hour": _fmt_hour(over.upper),
                "timezone": "UTC",
            },
        )

    def _parse(self, raw: object, variables: Sequence[str]) -> TimelineDelivery:
        """The envelope as ticks plus named series — vendor keys, vendor units, vendor length.

        The echoed `latitude` / `longitude` are deliberately dropped: the point is the one asked for,
        and re-deriving it from the response would answer a question already settled.
        """
        if not isinstance(raw, Mapping):
            raise RuntimeFailure("open-meteo response is not a JSON object")
        try:
            hourly = raw["hourly"]
            units = raw["hourly_units"]
            stamps = hourly["time"]
        except (KeyError, TypeError) as exc:
            raise RuntimeFailure("open-meteo response missing required forecast fields") from exc

        if not isinstance(hourly, Mapping) or not isinstance(units, Mapping):
            raise RuntimeFailure("open-meteo hourly payload is malformed")
        if not isinstance(stamps, Sequence) or len(stamps) == 0:
            raise RuntimeFailure("open-meteo hourly time axis is malformed")

        valid_time = [_parse_utc_hour(stamp) for stamp in stamps]
        series: dict[str, Sequence[float | None]] = {}
        for name in variables:
            values = hourly.get(name)
            if not isinstance(values, Sequence) or len(values) != len(valid_time):
                raise RuntimeFailure(f"open-meteo hourly array malformed for {name}")
            series[name] = [_optional_float(cell, name) for cell in values]

        return TimelineDelivery(
            valid_time=valid_time,
            series=series,
            reported_units={name: token for name, token in units.items() if isinstance(token, str)},
        )


def _optional_float(cell: object, name: str) -> float | None:
    if cell is None:
        return None
    if isinstance(cell, bool):
        raise RuntimeFailure(f"open-meteo value for {name} is not numeric")
    if isinstance(cell, (int, float)):
        return float(cell)
    if isinstance(cell, str):
        try:
            return float(cell)
        except ValueError as exc:
            raise RuntimeFailure(f"open-meteo value for {name} is not numeric") from exc
    raise RuntimeFailure(f"open-meteo value for {name} is not numeric")


def _fmt_coord(value: float) -> str:
    return format(value, ".15g")


def _fmt_hour(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M")


def _parse_utc_hour(stamp: object) -> datetime:
    if not isinstance(stamp, str):
        raise RuntimeFailure("open-meteo hourly time is not a string")
    try:
        parsed = datetime.fromisoformat(stamp)
    except ValueError as exc:
        raise RuntimeFailure(f"open-meteo hourly time is not ISO: {stamp!r}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def build(
    spec: OfferingSpec,
    settings: Mapping[str, object],
    secret_value: str | None,
    clock: Clock,
    parameters: ParameterTable,
) -> Provider:
    """Catalogue `build` face — composes the shape with this vendor's Probe and declarations."""
    if settings:
        raise CompositionError(f"open-meteo unknown settings keys: {', '.join(sorted(settings))}")
    del secret_value  # keyless
    return RollingTimeline(
        probe=OpenMeteoProbe(HttpxTransport(BASE_URL)),
        taps=TAPS,
        step=HOURLY_STEP,
        cadence=CADENCE,
        clock=clock,
        parameters=parameters,
        source_key=SourceKey(provider=PROVIDER_ID, dataset=spec.name),
    )


MANIFEST = ProviderManifest(
    impl_id=IMPL_ID,
    provider_id=PROVIDER_ID,
    offerings={
        BEST_MATCH: OfferingSpec(
            name=BEST_MATCH,
            parameters=_CANONICAL_IDS,
            store=StoreSpec(spatial_step=0.0001, retention_interval=timedelta(days=14)),
        )
    },
    secret=None,
    build=build,
    default_offering=BEST_MATCH,
)
