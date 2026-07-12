"""Open-Meteo vendor leaf — provider, scalar normalizer, cadence, and catalogue `MANIFEST`.

Phase C serves `air_temperature` only (`temperature_2m` ↔ 1:1). Channel / remaining parameters land
at issue 002. Session 0009 owns the HTTP mapping and transport policy.
"""

from __future__ import annotations

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
    Interval,
    RegularAxis,
    RegularDomain,
    Separable,
)
from ...manifold.provenance import AtomicOrigin, Provenance, Uniform
from ...parameters import AIR_TEMPERATURE
from ..catalog.paramtable import ParameterTable
from ..catalog.providers import OfferingSpec, ProviderManifest
from .base import FetchRequest, HttpxTransport, Provider, Transport

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

_VENDOR_TEMP_UNITS = frozenset({"°C", "degC"})
_HOURLY_STEP = timedelta(hours=1)
_NEAR_SURFACE_Z = Interval(0.0, 10.0)


class OpenMeteoNormalizer:
    """Maps Open-Meteo forecast JSON → native-geometry `Coverage` (semantics only; no Selection)."""

    def __init__(self, parameters: ParameterTable) -> None:
        self._parameters = parameters

    def normalize(self, raw: object, provenance: Provenance) -> Coverage:
        if not isinstance(raw, Mapping):
            raise RuntimeFailure("open-meteo response is not a JSON object")

        try:
            latitude = float(raw["latitude"])
            longitude = float(raw["longitude"])
            hourly = raw["hourly"]
            units = raw["hourly_units"]
            times_raw = hourly["time"]
            values_raw = hourly["temperature_2m"]
            unit = units["temperature_2m"]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeFailure("open-meteo response missing required forecast fields") from exc

        if unit not in _VENDOR_TEMP_UNITS:
            raise RuntimeFailure(f"open-meteo temperature unit mismatch: {unit!r}")

        if not isinstance(times_raw, Sequence) or not isinstance(values_raw, Sequence):
            raise RuntimeFailure("open-meteo hourly arrays are malformed")
        if len(times_raw) == 0 or len(times_raw) != len(values_raw):
            raise RuntimeFailure("open-meteo hourly time/value length mismatch")

        times = [_parse_utc_hour(stamp) for stamp in times_raw]
        for i, tick in enumerate(times):
            if tick != times[0] + _HOURLY_STEP * i:
                raise RuntimeFailure("open-meteo hourly time axis is not hourly")

        values: list[float] = []
        present: list[bool] = []
        for cell in values_raw:
            if cell is None:
                values.append(float("nan"))
                present.append(False)
            else:
                try:
                    values.append(float(cell))
                except (TypeError, ValueError) as exc:
                    raise RuntimeFailure("open-meteo temperature value is not numeric") from exc
                present.append(True)

        domain = RegularDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, longitude, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, latitude, 1.0, 1, False),
                AxisName.Z: RegularAxis(AxisName.Z, 2.0, 1.0, 1, False),
                AxisName.T: RegularAxis(AxisName.T, times[0], _HOURLY_STEP, len(times), False),
            }
        )
        definition = self._parameters.get(AIR_TEMPERATURE)
        return CoverageRecord(
            capability=EnumerableCapability(
                domain=domain,
                parameters={AIR_TEMPERATURE: definition},
            ),
            ranges={
                AIR_TEMPERATURE: ParameterData(
                    values=values,
                    present=None if all(present) else present,
                )
            },
            provenance=Uniform(provenance),
        )


class OpenMeteoProvider(Provider):
    """Open-Meteo forecast leaf — Selection → fetch → normalize, with authored provenance."""

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
        request = _forecast_request(selection)
        raw = await self._transport.fetch(request)
        now = self._clock.now()
        provenance = Provenance(
            origin=AtomicOrigin(self._source_key, self._cadence.anchor(now)),
            fetched_at=now,
            expiration=self._cadence.expiration(now),
        )
        return self._normalizer.normalize(raw, provenance)

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
    footprint = FootprintDomain(
        axes={
            AxisName.X: ContinuousAxis(AxisName.X, Interval(-180.0, 180.0)),
            AxisName.Y: ContinuousAxis(AxisName.Y, Interval(-90.0, 90.0)),
            AxisName.Z: ContinuousAxis(AxisName.Z, _NEAR_SURFACE_Z),
            AxisName.T: RollingAxis(AxisName.T, cadence, clock),
        }
    )
    definition = parameters.get(AIR_TEMPERATURE)
    return FootprintCapability(footprints={AIR_TEMPERATURE: (definition, footprint)})


def _forecast_request(selection: Selection) -> FetchRequest:
    domain = selection.domain
    if not isinstance(domain, Separable):
        raise RuntimeFailure("open-meteo Selection domain must be separable")
    if selection.parameters != frozenset({AIR_TEMPERATURE}):
        raise RuntimeFailure("open-meteo Phase C leaf serves air_temperature only")

    lon = domain.axis(AxisName.X).extent.lower
    lat = domain.axis(AxisName.Y).extent.lower
    t_extent = domain.axis(AxisName.T).extent
    if not isinstance(lon, float) or not isinstance(lat, float):
        raise RuntimeFailure("open-meteo Selection X/Y must be spatial floats")
    if not isinstance(t_extent.lower, datetime) or not isinstance(t_extent.upper, datetime):
        raise RuntimeFailure("open-meteo Selection T must be datetime")

    return FetchRequest(
        path="/v1/forecast",
        params={
            "latitude": _fmt_coord(lat),
            "longitude": _fmt_coord(lon),
            "hourly": "temperature_2m",
            "start_hour": _fmt_hour(t_extent.lower),
            "end_hour": _fmt_hour(t_extent.upper),
            "timezone": "UTC",
        },
    )


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
    del settings, secret_value  # keyless; no offering settings in Phase C
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
            parameters=frozenset({AIR_TEMPERATURE}),
            store=StoreSpec(spatial_step=0.0001, retention_interval=timedelta(days=14)),
        )
    },
    secret=None,
    build=build,
)
