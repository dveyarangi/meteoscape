"""TWC vendor leaf — Hourly Forecast Enterprise as a `TimelineProbe` and its declarations.

Vendor documentation (Google Docs behind `twcapi.co` shortlinks). Units are not self-reported, so
these pages — not the payload — are the only evidence for what the numbers mean:

- portfolio: https://docs.google.com/document/d/1pXDXkT4wd4I77LxkBnltQ7tKG4GlOsDeRUPdaDDtAW8
- enterprise hourly: https://twcapi.co/v3FODHE

Same point-plus-hourly-series shape as Open-Meteo, so this leaf adds no wrapper.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
from ..catalog.providers import OfferingSpec, ProviderManifest, SecretSlot
from .base import FetchRequest, HttpxTransport, Provider, Transport
from .normalization import u_component, v_component
from .timeline import (
    HOURLY_STEP,
    Z_1_5M,
    Z_10M,
    Z_COLUMN,
    Z_SURFACE,
    PointSeriesTap,
    TapTable,
    TimelineDelivery,
    TimelineProvider,
    VendorVar,
    passthrough,
    pointwise,
)

BASE_URL = "https://api.weather.com"
IMPL_ID = PROVIDER_ID = "twc"
DEFAULT_OFFERING = "hourly_10day"
DEFAULT_CADENCE_HOURS = 12
"""Polling interval. Policy, not a vendor fact — `build` applies it when settings omit `cadence_hours`."""

_CANONICAL_IDS: frozenset[ParameterId] = frozenset(
    {AIR_TEMPERATURE, RELATIVE_HUMIDITY, WIND_U, WIND_V, PRECIPITATION, CLOUD_COVER}
)

_STORE = StoreSpec(spatial_step=0.0001, retention_interval=timedelta(days=14))


@dataclass(frozen=True)
class _Duration:
    segment: str
    max_lead: timedelta


_DURATIONS: Mapping[str, _Duration] = {
    "hourly_6hour": _Duration("6hour", timedelta(hours=5)),
    "hourly_12hour": _Duration("12hour", timedelta(hours=11)),
    "hourly_1day": _Duration("1day", timedelta(hours=23)),
    "hourly_2day": _Duration("2day", timedelta(hours=47)),
    "hourly_3day": _Duration("3day", timedelta(hours=71)),
    "hourly_10day": _Duration("10day", timedelta(hours=239)),
    "hourly_15day": _Duration("15day", timedelta(hours=359)),
}

_wind_u = pointwise("windSpeed", "windDirection", fn=u_component)
_wind_v = pointwise("windSpeed", "windDirection", fn=v_component)

_WIND_VARS = (
    VendorVar("windSpeed", "km/h"),
    VendorVar("windDirection", "°"),
)

TAPS = TapTable(
    (
        PointSeriesTap(
            produces=AIR_TEMPERATURE,
            vendor_vars=(VendorVar("temperature", "°C"),),
            z=Z_1_5M,
            decode=passthrough("temperature"),
        ),
        PointSeriesTap(
            produces=RELATIVE_HUMIDITY,
            vendor_vars=(VendorVar("relativeHumidity", "%"),),
            z=Z_1_5M,  # height not documented; same screen instrument as temperature
            decode=passthrough("relativeHumidity"),
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
            vendor_vars=(VendorVar("qpf", "mm"),),
            z=Z_SURFACE,
            decode=passthrough("qpf"),
        ),
        PointSeriesTap(
            produces=CLOUD_COVER,
            vendor_vars=(VendorVar("cloudCover", "%"),),
            z=Z_COLUMN,
            decode=passthrough("cloudCover"),
        ),
    )
)


class TwcProbe:
    """TWC's enterprise hourly endpoint: one query built, one envelope parsed, nothing interpreted.

    The vendor takes no window and no field list — it returns its whole series with every field.
    `over` is therefore unused; `variables` still names what `_parse` slices out of that envelope.
    """

    reports_units = False
    """TWC publishes no unit map; units are chosen by the request `units` param and never echoed."""

    def __init__(self, transport: Transport, *, duration: str, api_key: str) -> None:
        self._transport = transport
        self._duration = duration
        self._api_key = api_key

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
        del over, variables
        return FetchRequest(
            path=f"/v3/wx/forecast/hourly/{self._duration}/enterprise",
            params={
                "geocode": f"{_fmt_coord(latitude)},{_fmt_coord(longitude)}",
                "units": "m",
                "language": "en-US",
                "format": "json",
                "apiKey": self._api_key,
            },
        )

    def _parse(self, raw: object, variables: Sequence[str]) -> TimelineDelivery:
        """The envelope as ticks plus named series — a flat object of parallel lists, no unit map."""
        if not isinstance(raw, Mapping):
            raise RuntimeFailure("twc response is not a JSON object")
        try:
            stamps = raw["validTimeUtc"]
        except KeyError as exc:
            raise RuntimeFailure("twc response missing required forecast fields") from exc

        if not isinstance(stamps, Sequence) or isinstance(stamps, (str, bytes)) or len(stamps) == 0:
            raise RuntimeFailure("twc validTimeUtc axis is malformed")

        valid_time = [_parse_epoch(stamp) for stamp in stamps]
        series: dict[str, Sequence[float | None]] = {}
        for name in variables:
            values = raw.get(name)
            if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
                raise RuntimeFailure(f"twc series malformed for {name}")
            if len(values) != len(valid_time):
                raise RuntimeFailure(f"twc series malformed for {name}")
            series[name] = [_optional_float(cell, name) for cell in values]

        return TimelineDelivery(valid_time=valid_time, series=series, reported_units=None)


def _optional_float(cell: object, name: str) -> float | None:
    if cell is None:
        return None
    if isinstance(cell, bool):
        raise RuntimeFailure(f"twc value for {name} is not numeric")
    if isinstance(cell, (int, float)):
        return float(cell)
    raise RuntimeFailure(f"twc value for {name} is not numeric")


def _fmt_coord(value: float) -> str:
    return format(value, ".15g")


def _parse_epoch(stamp: object) -> datetime:
    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
        raise RuntimeFailure("twc validTimeUtc is not a UNIX epoch")
    return datetime.fromtimestamp(int(stamp), tz=UTC)


def build(
    spec: OfferingSpec,
    settings: Mapping[str, object],
    secret_value: str | None,
    clock: Clock,
    parameters: ParameterTable,
) -> Provider:
    """Catalogue `build` face — composes the shape with this vendor's Probe and declarations."""
    if secret_value is None:
        raise CompositionError("twc requires an API key; set METEOSCAPE_TWC_API_KEY")
    unknown = sorted(key for key in settings if key != "cadence_hours")
    if unknown:
        raise CompositionError(f"twc unknown settings keys: {', '.join(unknown)}")
    duration = _DURATIONS[spec.name]
    hours = settings.get("cadence_hours", DEFAULT_CADENCE_HOURS)
    if not isinstance(hours, int) or isinstance(hours, bool) or hours <= 0:
        raise CompositionError(f"twc cadence_hours must be a positive integer, got {hours!r}")
    try:
        cadence = CadenceDef(
            # Δ is our polling interval: TWC publishes no run schedule (ADR-0003 bucket regime).
            cadence=timedelta(hours=hours),
            # L = 0: no runs means no publication delay; a non-zero L slides the bucket off its grid.
            publication_latency=timedelta(0),
            max_lead=duration.max_lead,
            # Hourly Shelf, independent of Δ. Declaring late is the safe direction; the retention
            # predicate (ADR-0002) absorbs the at-most-one-hour over-declaration of a series that
            # starts at the next whole hour.
            shelf=timedelta(hours=1),
        )
    except ValueError as exc:
        raise CompositionError(
            f"twc {spec.name}: cadence_hours={hours} exceeds this offering's horizon "
            f"{duration.max_lead}; choose a smaller cadence_hours"
        ) from exc
    return TimelineProvider(
        probe=TwcProbe(HttpxTransport(BASE_URL), duration=duration.segment, api_key=secret_value),
        taps=TAPS,
        step=HOURLY_STEP,
        cadence=cadence,
        clock=clock,
        parameters=parameters,
        source_key=SourceKey(provider=PROVIDER_ID, dataset=spec.name),
    )


MANIFEST = ProviderManifest(
    impl_id=IMPL_ID,
    provider_id=PROVIDER_ID,
    offerings={
        name: OfferingSpec(name=name, parameters=_CANONICAL_IDS, store=_STORE)
        for name in _DURATIONS
    },
    secret=SecretSlot("api_key"),
    build=build,
    default_offering=DEFAULT_OFFERING,
)
