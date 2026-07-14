"""Open-Meteo vendor leaf — provider, normalizer, cadence, and catalogue `MANIFEST`.

Serves the 6 canonical parameters via a `PointSeriesTap` table (timeline shape — see `timeline.py`).
Session 0009 owns the HTTP mapping; ticket 002 owns the tap / native-record contract.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

from ...clock import Clock
from ...config import StoreSpec
from ...errors import RuntimeFailure
from ...identity import SourceKey
from ...manifold.cadence import CadenceDef, RollingAxis
from ...manifold.capability import Capability, EnumerableCapability, FootprintCapability
from ...manifold.core import Coverage, Manifold, Selection
from ...manifold.coverage import CoverageRecord
from ...manifold.data import ParameterData
from ...manifold.domain import (
    AxisName,
    ContinuousAxis,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
    Separable,
)
from ...manifold.provenance import AtomicOrigin, Provenance, Uniform
from ...parameters import (
    AIR_TEMPERATURE,
    CLOUD_COVER,
    PRECIPITATION,
    RELATIVE_HUMIDITY,
    WIND_U,
    WIND_V,
    ParameterDef,
    ParameterId,
)
from ..catalog.paramtable import ParameterTable
from ..catalog.providers import OfferingSpec, ProviderManifest
from .base import FetchRequest, HttpxTransport, Provider, Transport
from .normalization import kmh_to_ms
from .timeline import (
    HOURLY_STEP,
    Z_2M,
    Z_10M,
    Z_COLUMN,
    Z_SURFACE,
    AxisSpec,
    PointSeriesTap,
    VendorVar,
    axis,
    cell,
    passthrough,
)

BASE_URL = "https://api.open-meteo.com"
IMPL_ID = "open-meteo"
PROVIDER_ID = "open-meteo"
BEST_MATCH = "best_match"

# Conservative cadence — concern #18 owns refinement; not operator-tunable before it means something.
CADENCE = CadenceDef(
    cadence=timedelta(hours=1),
    publication_latency=timedelta(hours=1),
    max_lead=timedelta(days=16),
)

_CANONICAL_IDS: frozenset[ParameterId] = frozenset(
    {AIR_TEMPERATURE, RELATIVE_HUMIDITY, WIND_U, WIND_V, PRECIPITATION, CLOUD_COVER}
)


def _wind_u(arrays: Mapping[str, Sequence[float | None]]) -> list[float]:
    return [
        _wind_component(cell(s), cell(d), u=True)
        for s, d in zip(arrays["wind_speed_10m"], arrays["wind_direction_10m"], strict=True)
    ]


def _wind_v(arrays: Mapping[str, Sequence[float | None]]) -> list[float]:
    return [
        _wind_component(cell(s), cell(d), u=False)
        for s, d in zip(arrays["wind_speed_10m"], arrays["wind_direction_10m"], strict=True)
    ]


def _wind_component(speed_ms: float, direction_deg: float, *, u: bool) -> float:
    if math.isnan(speed_ms) or math.isnan(direction_deg):
        return float("nan")
    rad = math.radians(direction_deg)
    # Meteorological direction: degrees FROM which the wind blows.
    return (-speed_ms * math.sin(rad)) if u else (-speed_ms * math.cos(rad))


_WIND_VARS = (
    VendorVar("wind_speed_10m", "km/h"),
    VendorVar("wind_direction_10m", "°"),
)

TAPS: tuple[PointSeriesTap, ...] = (
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


class OpenMeteoNormalizer:
    """Maps Open-Meteo forecast JSON → native-geometry records (semantics only; no Selection)."""

    def __init__(self, parameters: ParameterTable) -> None:
        self._parameters = parameters

    def normalize(
        self,
        raw: object,
        provenance: Provenance,
        *,
        parameters: frozenset[ParameterId] | None = None,
    ) -> Sequence[Coverage]:
        if not isinstance(raw, Mapping):
            raise RuntimeFailure("open-meteo response is not a JSON object")

        wanted = _CANONICAL_IDS if parameters is None else parameters & _CANONICAL_IDS
        taps = tuple(tap for tap in TAPS if tap.produces in wanted)
        if not taps:
            raise RuntimeFailure("open-meteo normalize received no recognised parameters")

        try:
            latitude = float(raw["latitude"])
            longitude = float(raw["longitude"])
            hourly = raw["hourly"]
            units = raw["hourly_units"]
            times_raw = hourly["time"]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeFailure("open-meteo response missing required forecast fields") from exc

        if not isinstance(hourly, Mapping) or not isinstance(units, Mapping):
            raise RuntimeFailure("open-meteo hourly payload is malformed")
        if not isinstance(times_raw, Sequence) or len(times_raw) == 0:
            raise RuntimeFailure("open-meteo hourly time axis is malformed")

        times = [_parse_utc_hour(stamp) for stamp in times_raw]
        for i, tick in enumerate(times):
            if tick != times[0] + HOURLY_STEP * i:
                raise RuntimeFailure("open-meteo hourly time axis is not hourly")
        n = len(times)

        converted = _converted_vendor_arrays(hourly, units, taps, n)

        groups: dict[AxisSpec, list[PointSeriesTap]] = defaultdict(list)
        for tap in taps:
            groups[tap.z].append(tap)

        records: list[Coverage] = []
        for z_spec, group in groups.items():
            ranges: dict[ParameterId, ParameterData] = {}
            defs: dict[ParameterId, ParameterDef] = {}
            for tap in group:
                values = tap.decode(
                    {var.name: converted[var.name] for var in tap.vendor_vars}
                )
                if len(values) != n:
                    raise RuntimeFailure(
                        f"open-meteo decode length mismatch for {tap.produces}: "
                        f"{len(values)} != {n}"
                    )
                ranges[tap.produces] = ParameterData(values=values, present=None)
                defs[tap.produces] = self._parameters.get(tap.produces)

            domain = GridDomain(
                axes={
                    AxisName.X: RegularAxis(AxisName.X, longitude, 1.0, 1, False),
                    AxisName.Y: RegularAxis(AxisName.Y, latitude, 1.0, 1, False),
                    AxisName.Z: axis(z_spec),
                    AxisName.T: RegularAxis(AxisName.T, times[0], HOURLY_STEP, n, True),
                }
            )
            records.append(
                CoverageRecord(
                    capability=EnumerableCapability(domain=domain, parameters=defs),
                    ranges=ranges,
                    provenance=Uniform(provenance),
                )
            )
        return records


class OpenMeteoProvider(Provider):
    """Open-Meteo forecast leaf — Selection → fetch-once → native records → assemble on `sel.domain`."""

    def __init__(
        self,
        *,
        transport: Transport,
        clock: Clock,
        parameters: ParameterTable,
        dataset: str = BEST_MATCH,
        cadence: CadenceDef = CADENCE,
        normalizer: OpenMeteoNormalizer | None = None,
    ) -> None:
        self._transport = transport
        self._clock = clock
        self._parameters = parameters
        self._dataset = dataset
        self._cadence = cadence
        self._normalizer = normalizer or OpenMeteoNormalizer(parameters)
        self._source_key = SourceKey(provider=PROVIDER_ID, dataset=dataset)
        self._capability = _build_capability(clock, cadence, parameters)

    async def project(self, selection: Selection) -> Manifold:
        taps = tuple(tap for tap in TAPS if tap.produces in selection.parameters)
        if not taps:
            raise RuntimeFailure("open-meteo Selection requests no served parameters")
        request = _forecast_request(selection, taps)
        raw = await self._transport.fetch(request)
        now = self._clock.now()
        provenance = Provenance(
            origin=AtomicOrigin(self._source_key, self._cadence.anchor(now)),
            fetched_at=now,
            expiration=self._cadence.expiration(now),
        )
        records = self._normalizer.normalize(
            raw, provenance, parameters=frozenset(tap.produces for tap in taps)
        )
        return _assemble(records, selection)

    @property
    def capability(self) -> Capability:
        return self._capability

    @property
    def source_key(self) -> SourceKey:
        return self._source_key


def _build_capability(
    clock: Clock,
    cadence: CadenceDef,
    parameters: ParameterTable,
) -> FootprintCapability:
    footprints: dict[ParameterId, tuple[ParameterDef, FootprintDomain]] = {}
    xy_t = {
        AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
        AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
        AxisName.T: RollingAxis(AxisName.T, cadence, clock),
    }
    for tap in TAPS:
        footprint = FootprintDomain(
            axes={**xy_t, AxisName.Z: axis(tap.z)},
        )
        footprints[tap.produces] = (parameters.get(tap.produces), footprint)
    return FootprintCapability(footprints=footprints)


def _forecast_request(selection: Selection, taps: Sequence[PointSeriesTap]) -> FetchRequest:
    domain = selection.domain
    if not isinstance(domain, Separable):
        raise RuntimeFailure("open-meteo Selection domain must be separable")

    lon = domain.axis(AxisName.X).extent.lower
    lat = domain.axis(AxisName.Y).extent.lower
    t_extent = domain.axis(AxisName.T).extent
    if not isinstance(lon, float) or not isinstance(lat, float):
        raise RuntimeFailure("open-meteo Selection X/Y must be spatial floats")
    if not isinstance(t_extent.lower, datetime) or not isinstance(t_extent.upper, datetime):
        raise RuntimeFailure("open-meteo Selection T must be datetime")

    hourly_vars: list[str] = []
    seen: set[str] = set()
    for tap in taps:
        for var in tap.vendor_vars:
            if var.name not in seen:
                seen.add(var.name)
                hourly_vars.append(var.name)

    return FetchRequest(
        path="/v1/forecast",
        params={
            "latitude": _fmt_coord(lat),
            "longitude": _fmt_coord(lon),
            "hourly": ",".join(hourly_vars),
            "start_hour": _fmt_hour(t_extent.lower),
            "end_hour": _fmt_hour(t_extent.upper),
            "timezone": "UTC",
        },
    )


def _assemble(records: Sequence[Coverage], selection: Selection) -> CoverageRecord:
    """Interim fold: native records → one Coverage on `sel.domain` (value passthrough; Z relabel)."""
    if not isinstance(selection.domain, GridDomain):
        raise RuntimeFailure("open-meteo assemble requires a GridDomain selection")

    ranges: dict[ParameterId, ParameterData] = {}
    parameters: dict[ParameterId, ParameterDef] = {}
    provenance_field = None
    n = len(selection.domain)

    for record in records:
        if provenance_field is None:
            provenance_field = record.provenance
        for pid, data in record.ranges.items():
            if pid not in selection.parameters:
                continue
            if len(data.values) != n:
                raise RuntimeFailure(
                    f"open-meteo native record length {len(data.values)} "
                    f"does not match selection size {n} for {pid}"
                )
            ranges[pid] = data
            parameters[pid] = record.capability.parameters[pid]

    missing = selection.parameters - ranges.keys()
    if missing:
        raise RuntimeFailure(f"open-meteo assemble missing parameter(s): {sorted(missing)}")
    if provenance_field is None:
        raise RuntimeFailure("open-meteo assemble received no native records")

    return CoverageRecord(
        capability=EnumerableCapability(
            domain=selection.domain,
            parameters=parameters,
        ),
        ranges=ranges,
        provenance=provenance_field,
    )


def _converted_vendor_arrays(
    hourly: Mapping[str, object],
    units: Mapping[str, object],
    taps: Sequence[PointSeriesTap],
    n: int,
) -> dict[str, list[float | None]]:
    """Verify `hourly_units`, convert-on-ingest (wind km/h→m/s), return per-var series."""
    needed: dict[str, VendorVar] = {}
    for tap in taps:
        for var in tap.vendor_vars:
            needed[var.name] = var

    out: dict[str, list[float | None]] = {}
    for name, expected in needed.items():
        reported = units.get(name)
        if not isinstance(reported, str) or not _units_match(reported, expected.unit):
            raise RuntimeFailure(
                f"open-meteo unit mismatch for {name}: expected {expected.unit!r}, got {reported!r}"
            )
        raw_series = hourly.get(name)
        if not isinstance(raw_series, Sequence) or len(raw_series) != n:
            raise RuntimeFailure(f"open-meteo hourly array malformed for {name}")
        series = [_optional_float(cell, name) for cell in raw_series]
        if expected.unit == "km/h":
            series = [None if v is None else kmh_to_ms(v) for v in series]
        out[name] = series
    return out


def _units_match(reported: str, expected: str) -> bool:
    if reported == expected:
        return True
    aliases = {
        "°C": {"°C", "degC", "celsius"},
        "degC": {"°C", "degC", "celsius"},
        "%": {"%", "percent"},
        "°": {"°", "degree", "degrees"},
        "km/h": {"km/h", "kmh"},
        "mm": {"mm"},
    }
    return reported in aliases.get(expected, {expected})


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
    """Catalogue `build` face — constructs the real `HttpxTransport` (tests inject via ctor)."""
    del settings, secret_value  # keyless; no offering settings in v1
    return OpenMeteoProvider(
        transport=HttpxTransport(BASE_URL),
        clock=clock,
        parameters=parameters,
        dataset=spec.name,
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
)
