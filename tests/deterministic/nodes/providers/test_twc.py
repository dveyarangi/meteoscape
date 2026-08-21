"""TWC leaf — its Probe's query and envelope parse, and the shape it is composed into."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fakes import STOPPED, core_parameters
from meteoscape.clock import StoppedClock
from meteoscape.errors import CompositionError, RuntimeFailure
from meteoscape.identity import SourceKey
from meteoscape.manifold.cadence import CadenceDef, RollingAxis
from meteoscape.manifold.core import Selection
from meteoscape.manifold.coverage import CoverageSet
from meteoscape.manifold.domain import (
    AxisName,
    FootprintDomain,
    GridDomain,
    Interval,
    RegularAxis,
    SelectionDomain,
    SnappedAxis,
)
from meteoscape.nodes.providers.base import FetchRequest, Provider, Transport
from meteoscape.nodes.providers.timeline import (
    HOURLY_STEP,
    TOA_M,
    Z_1_5M,
    Z_10M,
    Z_COLUMN,
    Z_SURFACE,
    RollingTimeline,
    TimelineDelivery,
)
from meteoscape.nodes.providers.twc import (
    PROVIDER_ID,
    TAPS,
    TwcProbe,
    build,
)
from meteoscape.parameters import (
    AIR_TEMPERATURE,
    CLOUD_COVER,
    PRECIPITATION,
    RELATIVE_HUMIDITY,
    WIND_U,
    WIND_V,
    ParameterId,
)

ALL_SERVED = frozenset(
    {AIR_TEMPERATURE, RELATIVE_HUMIDITY, WIND_U, WIND_V, PRECIPITATION, CLOUD_COVER}
)
_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "twc_hourly_10day.json").read_text(encoding="utf-8")
)
_WINDOW = Interval(
    datetime(2026, 8, 11, 12, tzinfo=UTC),
    datetime(2026, 8, 11, 15, tzinfo=UTC),
)
_CAPTURE_CLOCK = StoppedClock(datetime(2026, 8, 11, 12, 0, tzinfo=UTC))


class _CapturingTransport:
    def __init__(self, response: object) -> None:
        self.requests: list[FetchRequest] = []
        self._response = response

    async def fetch(self, request: FetchRequest) -> object:
        self.requests.append(request)
        return self._response


def _canned_hourly(*, hours: int = 4, start: datetime | None = None, **fields) -> dict:
    start = start or datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    epochs = [int((start + timedelta(hours=i)).timestamp()) for i in range(hours)]
    body = {
        "validTimeUtc": epochs,
        "temperature": [18.0 + i for i in range(hours)],
        "relativeHumidity": [50 + i for i in range(hours)],
        "qpf": [0.1 * i for i in range(hours)],
        "cloudCover": [40 + i for i in range(hours)],
        "windSpeed": [36] * hours,
        "windDirection": [90] * hours,
        "windGust": [None] * hours,
        "wxString": [None] * hours,
    }
    body.update(fields)
    return body


def _cadence(*, hours: int = 12, max_lead_hours: int = 239) -> CadenceDef:
    return CadenceDef(
        cadence=timedelta(hours=hours),
        publication_latency=timedelta(0),
        max_lead=timedelta(hours=max_lead_hours),
        shelf=timedelta(hours=1),
    )


def _provider(
    transport: Transport,
    *,
    duration: str = "10day",
    clock: StoppedClock = STOPPED,
    cadence: CadenceDef | None = None,
) -> RollingTimeline:
    return RollingTimeline(
        probe=TwcProbe(transport, duration=duration, api_key="secret"),
        taps=TAPS,
        step=HOURLY_STEP,
        cadence=cadence or _cadence(),
        clock=clock,
        parameters=core_parameters(),
        source_key=SourceKey(PROVIDER_ID, "hourly_10day"),
    )


async def _delivered(raw: object, *variables: str) -> TimelineDelivery:
    return await TwcProbe(_CapturingTransport(raw), duration="10day", api_key="secret").retrieve(
        longitude=13.41,
        latitude=52.52,
        over=_WINDOW,
        variables=variables,
    )


def _boundless_selection(*, parameters) -> Selection:
    return Selection(
        domain=SelectionDomain(
            axes={
                AxisName.X: RegularAxis(AxisName.X, 13.41, 1.0, 1, False),
                AxisName.Y: RegularAxis(AxisName.Y, 52.52, 1.0, 1, False),
                AxisName.Z: SnappedAxis(AxisName.Z),
                AxisName.T: SnappedAxis(AxisName.T),
            }
        ),
        parameters=frozenset(parameters),
    )


def _reached(answer: CoverageSet, pid: ParameterId) -> GridDomain:
    reach = answer.capability.reach(pid)
    assert isinstance(reach, GridDomain)
    return reach


def _t_axis(provider: Provider) -> RollingAxis:
    domain = provider.capability.reach(AIR_TEMPERATURE)
    assert isinstance(domain, FootprintDomain)
    axis = domain.axis(AxisName.T)
    assert isinstance(axis, RollingAxis)
    return axis


def _build(name: str = "hourly_10day", settings: dict | None = None, secret: str | None = "k"):
    from meteoscape.nodes.providers.twc import MANIFEST

    return build(MANIFEST.offerings[name], settings or {}, secret, STOPPED, core_parameters())


@pytest.mark.asyncio
async def test_query_is_enterprise_hourly_metric() -> None:
    transport = _CapturingTransport(_canned_hourly())
    probe = TwcProbe(transport, duration="10day", api_key="secret")
    await probe.retrieve(
        longitude=13.41,
        latitude=52.52,
        over=_WINDOW,
        variables=("temperature",),
    )
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.path == "/v3/wx/forecast/hourly/10day/enterprise"
    assert request.params == {
        "geocode": "52.52,13.41",
        "units": "m",
        "language": "en-US",
        "format": "json",
        "apiKey": "secret",
    }


@pytest.mark.asyncio
async def test_fixture_decodes_six_parameters_at_native_z_groups() -> None:
    transport = _CapturingTransport(_FIXTURE)
    provider = _provider(transport, clock=_CAPTURE_CLOCK)
    answer = await provider.project(_boundless_selection(parameters=ALL_SERVED))

    assert isinstance(answer, CoverageSet)
    assert set(answer.capability.parameters) == ALL_SERVED
    assert len(answer.records) == 4
    assert _reached(answer, AIR_TEMPERATURE).axis(AxisName.Z).extent.lower == pytest.approx(1.5)
    assert _reached(answer, RELATIVE_HUMIDITY).axis(AxisName.Z).extent.lower == pytest.approx(1.5)
    assert _reached(answer, WIND_U).axis(AxisName.Z).extent.lower == pytest.approx(10.0)
    assert _reached(answer, PRECIPITATION).axis(AxisName.Z).extent.lower == pytest.approx(0.0)
    assert _reached(answer, CLOUD_COVER).axis(AxisName.Z).extent.upper == pytest.approx(TOA_M)


def test_taps_group_temperature_and_humidity_at_screen_height() -> None:
    groups = TAPS.by_level()
    assert {spec: {tap.produces for tap in group} for spec, group in groups.items()} == {
        Z_1_5M: {AIR_TEMPERATURE, RELATIVE_HUMIDITY},
        Z_10M: {WIND_U, WIND_V},
        Z_SURFACE: {PRECIPITATION},
        Z_COLUMN: {CLOUD_COVER},
    }


@pytest.mark.asyncio
async def test_canned_wind_converts_integer_kmh_to_metres_per_second() -> None:
    delivery = await _delivered(_canned_hourly(hours=1), *TAPS.variables)
    values = TAPS.interpret(delivery, source=PROVIDER_ID)
    assert list(values[WIND_U].values) == pytest.approx([-10.0])
    assert list(values[WIND_V].values) == pytest.approx([0.0], abs=1e-9)


@pytest.mark.asyncio
async def test_epoch_ticks_are_aware_utc_on_the_hourly_step() -> None:
    delivery = await _delivered(_canned_hourly(hours=3), "temperature")
    assert delivery.valid_time == [
        datetime(2026, 8, 11, 12, tzinfo=UTC),
        datetime(2026, 8, 11, 13, tzinfo=UTC),
        datetime(2026, 8, 11, 14, tzinfo=UTC),
    ]
    transport = _CapturingTransport(_canned_hourly(hours=3))
    provider = _provider(transport, clock=_CAPTURE_CLOCK)
    answer = await provider.project(_boundless_selection(parameters={AIR_TEMPERATURE}))
    assert isinstance(answer, CoverageSet)
    ticks = _reached(answer, AIR_TEMPERATURE).axis(AxisName.T)
    assert isinstance(ticks, RegularAxis)
    assert ticks.step == HOURLY_STEP
    assert ticks.count == 3
    assert ticks[0].coordinate == datetime(2026, 8, 11, 12, tzinfo=UTC)


@pytest.mark.asyncio
async def test_malformed_envelope_is_runtime_failure_not_keyerror() -> None:
    with pytest.raises(RuntimeFailure, match="missing required"):
        await _delivered({}, "temperature")
    ragged = _canned_hourly(hours=4)
    ragged["temperature"] = [1.0, 2.0]
    with pytest.raises(RuntimeFailure, match="malformed"):
        await _delivered(ragged, "temperature")


def _declared_cadence(provider: Provider) -> CadenceDef:
    return _t_axis(provider).cadence


def test_build_defaults_cadence_and_accepts_an_override() -> None:
    assert _declared_cadence(_build()).cadence == timedelta(hours=12)
    assert _declared_cadence(_build(settings={"cadence_hours": 6})).cadence == timedelta(hours=6)


@pytest.mark.parametrize("hours", [0, -1, "12", True])
def test_build_rejects_invalid_cadence_hours(hours: object) -> None:
    with pytest.raises(CompositionError, match="cadence_hours"):
        _build(settings={"cadence_hours": hours})


@pytest.mark.parametrize(
    "name, horizon", [("hourly_6hour", "5:00:00"), ("hourly_12hour", "11:00:00")]
)
def test_build_refuses_an_offering_shorter_than_the_cadence(name: str, horizon: str) -> None:
    with pytest.raises(CompositionError, match=name) as exc:
        _build(name)
    message = str(exc.value)
    assert "cadence_hours=12" in message
    assert horizon in message
    assert "choose a smaller cadence_hours" in message
    assert isinstance(exc.value.__cause__, ValueError)


def test_build_accepts_a_short_offering_when_cadence_fits() -> None:
    cadence = _declared_cadence(_build("hourly_6hour", settings={"cadence_hours": 2}))
    assert cadence.max_lead == timedelta(hours=5)
    assert cadence.cadence == timedelta(hours=2)


def test_build_requires_a_secret() -> None:
    with pytest.raises(CompositionError, match="API key"):
        _build(secret=None)


def test_build_rejects_unknown_settings_keys() -> None:
    with pytest.raises(CompositionError, match="enabled") as exc:
        _build(settings={"cadence_hours": 6, "enabled": True})
    assert "cadence_hours" not in str(exc.value)


def test_declared_window_opens_on_the_current_hour() -> None:
    clock = StoppedClock(datetime(2026, 7, 11, 13, 30, tzinfo=UTC))
    from meteoscape.nodes.providers.twc import MANIFEST

    provider = build(MANIFEST.offerings["hourly_10day"], {}, "k", clock, core_parameters())
    assert _t_axis(provider).extent.lower == datetime(2026, 7, 11, 13, 0, tzinfo=UTC)
