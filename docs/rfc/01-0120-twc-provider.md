# TWC provider — implementation plan

**Authored:** 2026-08-11
**Last amended:** 2026-08-16

Implementation plan for [TWC provider](../tickets/01-0120-twc-provider.md) (legacy 011).

**Scope in one line:** a second vendor leaf — `TwcProbe` plus declarations — behind the existing
`TimelineProvider`, with seven enterprise offering rows, the first shipped `SecretSlot`, its parity
check, and the priority flip. **The flip is two integers; the Probe is the ticket.**

**Depends on [0119 — live-window edge tolerance](../tickets/done/01-0119-live-window-edge-tolerance.md)**
(added 2026-08-11 after the stage 0 capture). TWC's series starts at the next whole hour, which makes
the Reservoir's refill gate refetch on *every* request — one metered call per request. 0119 lands
first.

**What this ticket is really testing:** whether m4's shape/vendor split holds. If anything beyond a
Probe and its declarations must be written, that abstraction is wrong, and saying so is worth more
than working around it.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `TimelineProbe` — value types only | [edge/provider.md](../edge/provider.md) | New implementation. **No** `Domain`, `Selection`, `Coverage`, `Capability`, `Provenance`, `Clock` — pinned by the **existing** [test_probe_seam_guard.py](../../tests/deterministic/test_probe_seam_guard.py), which auto-discovers vendor modules, so `twc.py` is guarded on creation with nothing written (corrected 2026-08-11; an earlier draft called for a new guard and mis-cited the edge record as listing this unguarded). |
| Declared live window vs delivered series | [0119](../tickets/done/01-0119-live-window-edge-tolerance.md) | **Moved out of this ticket.** TWC's series starts at the *next* whole hour, so the declared window opens before any tick exists. Repaired there, ahead of this ticket. |
| `TimelineProvider` — the shape | [timeline.py](../../src/meteoscape/nodes/providers/timeline.py) | **Unchanged**, except one added Z constant (`Z_1_5M`). If it needs more, that is this ticket's finding. |
| Offering identity vs operator policy | [ADR-0005](../adr/0005-build-time-composition.md), ticket | **Identity → `OfferingDef.name`** (duration, a catalogue row, boot-checked). **Policy → `OfferingDef.settings`** (cadence). First use of `settings`, wired at [composition.py:94](../../src/meteoscape/nodes/composition.py) and unused since. |
| `SecretSlot` | [catalog/providers.py](../../src/meteoscape/nodes/catalog/providers.py) | First shipped manifest to declare one. The seam is already built and guarded; this exercises it. |
| Run identity (`AtomicOrigin.issue_time`) | [ADR-0003](../adr/0003-provenance-and-origin.md) | **Stretched, knowingly.** TWC publishes no run schedule, so Δ is our polling interval → [#18](../concerns.md#18-clock-anchored-footprint-fidelity). |
| Canonical units | [parameters.md](../parameters.md) | **No *new* conversion edge** — `units=m` reuses the inline km/h→m/s Open-Meteo already declares, so [010](../tickets/01-0122-unit-conversion-edge.md)'s trigger (a shared *catalogue*) stays unmet. |
| Tick semantics | [#48](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick) | **Not repaired here.** TWC happens to match the lattice; Open-Meteo does not → [0126](../tickets/01-0126-tick-convention-declaration.md). |
| MCP edge contract | [edge/mcp.md](../edge/mcp.md) | **Unchanged.** Same six parameters, same shape. A different producer may answer; nothing in the payload's contract moves. |

## Vendor facts (sourced 2026-08-11; the Probe's whole basis)

From the **Hourly Forecast — Enterprise** documentation (`https://twcapi.co/v3FODHE`) and the product
portfolio. Both are cited in the leaf's module docstring, because **TWC self-reports no units** — those
pages, not the payload, are the only evidence for what the numbers mean.

1. **Paths.** `https://api.weather.com/v3/wx/forecast/hourly/{duration}/enterprise`, where duration ∈
   `6hour, 12hour, 1day, 2day, 3day, 10day, 15day`. Duration is a path segment; `enterprise` is a
   suffix, not a prefix.
2. **Required query params, all five:** `geocode` (`"{lat},{lon}"`), `units`, `language`, `format`,
   `apiKey`. **`apiKey` travels in the query string**, not a header.
3. **No window parameter exists.** The vendor returns its whole series; `over` cannot be used.
4. **`units=m`** (Metric) → °C, percent, mm, percent, **km/h**, degree.
   **Chosen over `units=s` (Metric SI) on quantization, corrected 2026-08-11.** The two systems are
   **identical for four of six fields** and differ only in the wind unit — and the doc types matter:
   `windSpeed` is **Integer**, while `temperature` and `qpf` are Decimal. So `units=s` yields integer
   **m/s** (1.0 m/s steps) where `units=m` yields integer **km/h** (0.28 m/s steps), ~3.6× finer on the
   quantity feeding four of the eight exposed parameters. `units=m` **weakly dominates**: if the vendor
   stores m/s natively, km/h integers are a lossless re-quantization of the same steps; if it stores
   finer, km/h preserves more.
   The cost is one conversion, and it is **already built**: `TapTable._converted` branches on the
   *declared* unit (`if var.unit == "km/h"`, [timeline.py:441](../../src/meteoscape/nodes/providers/timeline.py)),
   so declaring `"km/h"` converts for free through the same inline edge Open-Meteo uses. **No new edge
   is added**, so [010](../tickets/01-0122-unit-conversion-edge.md)'s trigger — a shared *catalogue* of
   edges — stays unmet.
   **Risk this accepts:** since TWC reports no units, the conversion fires on our declaration alone. If
   the request's `units` were ever wrong, values would be silently divided by 3.6. Parity is the only
   thing that would catch it — which is what "parity-verified only" means in practice.
5. **No unit self-reporting.** `reports_units = False`; `TimelineDelivery.reported_units = None`.
6. **`validTimeUtc` is UNIX epoch seconds.**
7. **Field semantics, verbatim:** `temperature` *"measured by a thermometer 1.5 meters above the
   ground"*; `windSpeed` *"sustained wind speed at the top of the hour"*; `windDirection` and
   `cloudCover` *"hourly average"*; `qpf` *"forecasted measurable precipitation for the upcoming
   hour"*. Heights for `relativeHumidity` and `cloudCover` are **not stated**.
8. ~~**No refresh cadence is stated anywhere.**~~ **False — corrected 2026-08-11 by the live
   capture.** The *documentation* states none, but the **payload does**: `expirationTimeUtc`, one
   value per tick. Observed at a fetch of `11:42:44Z`: the first **7** ticks (12:00–18:00Z — exactly
   the `6hour` horizon) expire at `11:47:47Z`, ~5 min out; the remaining 233 expire at `12:03:25Z`,
   ~21 min out. So TWC refreshes a near-term head every ~5 min and its tail every ~20, consistent
   with the advertised 15-minute update capability, and it exposes a **two-tier** product behind one
   endpoint. We do **not** adopt it as our `expiration` — see
   [What `expiration` promises](#what-expiration-promises).
9. **Types matter for parity and for the units choice:** `temperature` and `qpf` are **Decimal**;
   `relativeHumidity`, `cloudCover`, `windSpeed`, `windDirection` are **Integer**.

### Confirmed by the live capture (2026-08-11, seven durations, the pilot site)

Stage 0 ran; every declaration below rested on vendor prose until it did.

- **The envelope is flat** — 42 parallel top-level lists, no container nesting. This was the one fact
  the documentation did not pin, and it confirms the point-plus-columnar-series shape, hence **no
  wrapper**.
- **Every inferred `max_lead` is exact.** 6hour→5 h, 12hour→11 h, 1day→23 h, 2day→47 h, 3day→71 h,
  10day→239 h, 15day→359 h; uniform 3600 s steps throughout. `_DURATIONS` needs no edit, and stage 5
  no longer has to discover these.
- **The series opens at the next whole hour**, identically across all seven durations
  (fetch `11:42:44Z` → first tick `12:00:00Z`). This is what 0119 exists for.
- **`windSpeed` arrives as integer km/h**, observed range 5…14 — i.e. **1.4–3.9 m/s**. Under
  `units=s` those ten days would have collapsed to four distinct integers. Fact 4's reasoning is not
  merely confirmed but underestimated.
- **All six canonical fields are present**; 36 undocumented extras ride along (`windGust`,
  `precipChance`, `temperatureDewPoint`, …), none of which this leaf reads.
- **`windGust` carries JSON `null`s**, so nodata is present in the payload as expected — not on a tap
  we declare, but it confirms the vendor uses `null` rather than a sentinel.

## Which cadence regime this provider is in

TWC is the first **bucket-regime** provider under
[ADR-0003 § Two regimes](../adr/0003-provenance-and-origin.md) (decided 2026-08-11): it publishes no
run schedule, so `L = 0`, `A = floor(fetched_at, Δ)` is a **Fetch bucket** rather than a run, and Δ is
our polling interval declared in the vendor's slot. Nothing about the run regime changes; gridded
products arriving later sit in it unchanged, and a deployment runs both at once.

The one thing that must not happen: a bucket recorded *as* a run. The
[forecast-run archive](../tickets/02-0134-forecast-run-archive-source.md) keys by run time, so when it
arrives it either declines runless producers or records the distinction — flagged there, not here.

The per-tick `expirationTimeUtc` (fact 8) does **not** move TWC out of the bucket regime: it is a
staleness signal, not a run schedule, so there is still no run time to record and `L = 0` stands.

## What `expiration` promises

Fact 8 raises the obvious question — the vendor tells us its data expires in ~5 minutes, so should
`Provenance.expiration` say so? **No, decided at the 2026-08-11 align.** `exp` at the MCP edge
promises *"we will serve nothing newer before this time"*
([edge/mcp.md](../edge/mcp.md)), and that is a statement about **our refresh policy**, not the
vendor's. A vendor refreshing underneath us does not make it false; it means fresher data existed and
we chose not to buy it — which is the whole point of a polling interval against a monthly allotment.

The decisive fact is that `expiration` already does **two** jobs from one field: the caller's
staleness bound ([mcp_app.py:250](../../src/meteoscape/api/mcp_app.py)) **and** the Reservoir's
serve-vs-refetch trigger ([reservoir.py:138](../../src/meteoscape/nodes/reservoir.py)). Adopting a
5-minute vendor expiry would set our refetch interval to 5 minutes — spending the allotment it was
chosen to conserve. Splitting the two roles is a real design, and it is not this ticket's.

So: **freshness stays operator policy at Δ = 12 h.** The vendor's signal is recorded as a known,
unused input — [ideas: freshness](../ideas.md#freshness) already names "model-cycle expiry" as the
intended source for exactly this, and the faster-nowcast case that would want it is
[#18](../concerns.md#18-clock-anchored-footprint-fidelity)'s escape hatch, not v1's need.

## The consequence that costs money, accepted knowingly

`expiration = floor_to(now − L, Δ) + Δ + L` ([cadence.py:23,27](../../src/meteoscape/manifold/cadence.py))
is **anchored to an epoch-spaced grid**, which is right when Δ is a real run cadence — the next run
genuinely does publish then. With Δ as *our polling interval* there is no event at 00:00/12:00, so the
anchoring produces a sawtooth TTL:

```
Δ=12h, L=1h
now = 13:30  → anchor 12:00 → exp 01:00 next day   → TTL 11.5 h
now = 00:30  → anchor 12:00 prev → exp 01:00       → TTL  0.5 h
```

Over uniformly-distributed fetch times the **mean TTL is ≈ Δ/2, not Δ** — so a steadily-used deployment
makes roughly **twice** the vendor calls that "12-hour cadence" implies. That runs directly against the
reason 12 h was chosen: conserving a **monthly allotment**. It also makes `exp` — which
[edge/mcp.md](../edge/mcp.md) promises as *"the caller's usable staleness bound"* — jump between
minutes and hours.

A polling interval wants a **rolling** TTL (`fetched_at + Δ`), which `CadenceDef` cannot express and
this ticket does not add. **Accepted here, recorded at
[#18](../concerns.md#18-clock-anchored-footprint-fidelity)**, and flagged as a real input to the
[vendor-call ledger](../tickets/02-0124-vendor-call-ledger.md): the first thing the meter will show is
whether the call count matches the cadence anyone believes is configured.

**A second, larger spend defect was found by the live capture and is *not* accepted here.** Because
TWC's series starts at the next whole hour while a `1h` Shelf floors to the current one, `now`
always sits in the declared-but-undelivered gap — and the refill gate compares the request against
the **declared** reach, so containment never holds and **every request refills**. That is one metered
call per request, dwarfing the Δ/2 effect above. It is repaired ahead of this ticket by
[0119](../tickets/done/01-0119-live-window-edge-tolerance.md), which this ticket now depends on.

## Facts about our own tree (verified 2026-08-11)

1. **`spec.name` already reaches `build`** and becomes `SourceKey.dataset`
   ([open_meteo.py:247](../../src/meteoscape/nodes/providers/open_meteo.py)), so seven offerings give
   seven distinct `SourceKey`s with no new plumbing.
2. **The binder refuses an unknown offering at boot** —
   `CompositionError(f"unknown offering {offering.name!r} …")`
   ([composition.py:84](../../src/meteoscape/nodes/composition.py)). This is why duration is a name.
3. **`OfferingDef.settings` flows to `build`** ([composition.py:94](../../src/meteoscape/nodes/composition.py));
   Open-Meteo's `build` does `del settings  # keyless; no offering settings in v1`.
4. **Unit verification is skipped when `reported_units is None`** —
   `if reported is not None:` in `TapTable._converted`
   ([timeline.py:429](../../src/meteoscape/nodes/providers/timeline.py)) — and the km/h conversion
   branches on `var.unit == "km/h"`, which TWC never declares. So declaring `"m/s"` yields passthrough
   with no verification. That *is* the "parity-verified only" state.
5. **`_records` only faults on a units contradiction** when the Probe claims to report them
   (`if self._probe.reports_units and delivery.reported_units is None`, [timeline.py:198](../../src/meteoscape/nodes/providers/timeline.py)).
6. **`_lattice_of` builds the T axis from delivered ticks** and checks them against the declared step
   ([timeline.py:227-239](../../src/meteoscape/nodes/providers/timeline.py)), so a wider-than-asked
   series is normal and the crop narrows it.
6b. **The wrapper — not the Probe — decides the natural fetch unit.**
   `engaged = self._taps if boundless else self._taps.engaged_by(...)`
   ([timeline.py:109](../../src/meteoscape/nodes/providers/timeline.py)), and the Reservoir's refill is
   always boundless on T. So TWC answers with the **whole tap table** on every refill, exactly as
   Open-Meteo does, and inherits its immunity to
   [#43](../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence) **without
   declaring anything**. This is the clearest evidence so far that m4's split holds: the policy a
   narrow-answering vendor would break sits above the vendor seam.
7. **`Settings.offerings()` emits `name="default"`** for TWC ([config.py:100-107](../../src/meteoscape/config.py))
   — not a catalogue row under this design — and `test_config.py` pins it in **two** tests, one of
   which (`test_twc_key_adds_fallback_offering`) is misnamed once TWC is primary.
8. **Parity evidence already scrubs secrets** — `scrub_secrets(..., secrets)` at
   [comparison.py:251](../../tests/parity/comparison.py) and in `format_summary`. Passing
   `settings.secrets()` covers the `apiKey` in the reference reader's URL.
9. **`Settings` is a `BaseSettings` with `env_prefix="METEOSCAPE_"`**, so `METEOSCAPE_TWC_API_KEY`
   populates the key with no bespoke handling — this answers session 0024's deferred *"decide the
   parity-key handling"*.

## Code shape

One new module, `src/meteoscape/nodes/providers/twc.py`, mirroring `open_meteo.py`. The one structural
difference: **`CadenceDef` is built in `build`, not as a module constant**, because `max_lead` varies
per offering and `cadence` comes from operator settings.

```python
BASE_URL = "https://api.weather.com"
IMPL_ID = PROVIDER_ID = "twc"
DEFAULT_CADENCE_HOURS = 12          # exported: Settings imports it, so one default exists
DEFAULT_OFFERING = "hourly_10day"   # exported for the same reason

_CANONICAL_IDS: frozenset[ParameterId] = frozenset(
    {AIR_TEMPERATURE, RELATIVE_HUMIDITY, WIND_U, WIND_V, PRECIPITATION, CLOUD_COVER}
)  # the same six Open-Meteo serves; TWC adds no parameter here

# Per-offering Source store. Same shape as Open-Meteo's: a per-point cache at the fidelity floor,
# 14-day retention. Operator-overridable per offering via `OfferingDef.store`.
_STORE = StoreSpec(spatial_step=0.0001, retention_interval=timedelta(days=14))

@dataclass(frozen=True)
class _Duration:
    segment: str        # the path segment
    max_lead: timedelta # ticks the series reaches, as (n_hours - 1)

# The single source of truth: offering name -> vendor duration.
_DURATIONS: Mapping[str, _Duration] = {
    "hourly_6hour":  _Duration("6hour",  timedelta(hours=5)),
    "hourly_12hour": _Duration("12hour", timedelta(hours=11)),
    "hourly_1day":   _Duration("1day",   timedelta(hours=23)),
    "hourly_2day":   _Duration("2day",   timedelta(hours=47)),
    "hourly_3day":   _Duration("3day",   timedelta(hours=71)),
    "hourly_10day":  _Duration("10day",  timedelta(hours=239)),
    "hourly_15day":  _Duration("15day",  timedelta(hours=359)),
}
```

**`max_lead` is inferred, not documented.** The pattern is Open-Meteo's — N·24 hourly ticks spanning
N·24−1 hours — applied to each duration. Stage 5 counts the ticks actually delivered and replaces these
values with observed ones.

**What a wrong `max_lead` actually costs** (corrected during the second review — an earlier draft said
"over-declaring raises `Shortfall`", which is false on the shipped path). The Reservoir's refill asks
with `ANY` on T, so `open_axes` is non-empty and
[timeline.py:109](../../src/meteoscape/nodes/providers/timeline.py) takes the boundless branch:
`return group` — the answer keeps the **delivery's own** geometry and `_delivered` is never called. So:

- **Over-declaring** does not fault. It over-promises the **narrated horizon** at the MCP edge (built
  from `Capability.reach`) and yields answers that stop early — which that edge already treats as
  honest disclosure through `valid_time`.
- **Under-declaring** narrows what is admitted; requests past it get a clean `capability-mismatch`.
- `Shortfall → RuntimeFailure` is reachable **only from a fully pinned request**, and no shipped
  surface issues one — the MCP edge's T is always snapped.

Both directions are therefore quiet. That is the argument for stage 5 counting ticks: nothing else
will tell us.

`MANIFEST.offerings` is **derived from `_DURATIONS`**, never written twice — so the binder's
name check and the build's duration lookup cannot drift:

```python
MANIFEST = ProviderManifest(
    impl_id=IMPL_ID,
    provider_id=PROVIDER_ID,
    offerings={
        name: OfferingSpec(name=name, parameters=_CANONICAL_IDS, store=_STORE)
        for name in _DURATIONS
    },
    secret=SecretSlot("twc_api_key"),
    build=build,
)
```

`build` reads both knobs and validates the policy one:

```python
def build(spec, settings, secret_value, clock, parameters) -> Provider:
    if secret_value is None:
        raise CompositionError("twc requires an API key; declare secret_ref on the offering")
    duration = _DURATIONS[spec.name]          # total by construction (offerings derive from it)
    hours = settings.get("cadence_hours", _DEFAULT_CADENCE_HOURS)
    if not isinstance(hours, int) or isinstance(hours, bool) or hours <= 0:
        raise CompositionError(f"twc cadence_hours must be a positive integer, got {hours!r}")
    return TimelineProvider(
        probe=TwcProbe(HttpxTransport(BASE_URL), duration=duration.segment, api_key=secret_value),
        taps=TAPS,
        step=HOURLY_STEP,
        cadence=CadenceDef(
            # Δ is our POLLING INTERVAL, not an observed run cadence: TWC publishes no run
            # schedule. It still feeds AtomicOrigin's issue_time -> #18. Operator-overridable.
            cadence=timedelta(hours=hours),
            # L = 0, not provisional: publication latency is run-time -> available, and this vendor
            # publishes no runs. A non-zero L would slide the bucket off its own grid.
            publication_latency=timedelta(0),
            max_lead=duration.max_lead,               # inferred; confirmed at stage 5
            # An hourly Shelf, INDEPENDENT of the polling interval. Without it the window falls
            # back to anchor(now) = floor_to(now - L, 12h), opening up to 13h before the vendor's
            # first tick. The vendor actually starts at the NEXT whole hour, so even 1h
            # over-declares - but by at most one hour, which 0119's retention predicate absorbs.
            # Declaring late is the safe direction: too-early admits hours the vendor never
            # publishes.
            shelf=timedelta(hours=1),
        ),
        clock=clock,
        parameters=parameters,
        source_key=SourceKey(provider=PROVIDER_ID, dataset=spec.name),
    )
```

**Taps.** Six, all `passthrough` except wind, reusing `u_component` / `v_component` exactly as
Open-Meteo does. Declared units are `°C`, `%`, `mm`, `%`, **`km/h`**, `°` — **what we requested via
`units=m`, unverifiable because the vendor publishes none** (facts 4/5). The `km/h` declaration is what
triggers the existing inline conversion; it is a declaration doing real work, not documentation. Z
levels:

| tap | vendor var(s) | Z | note |
|---|---|---|---|
| `AIR_TEMPERATURE` | `temperature` | **`Z_1_5M`** | documented 1.5 m |
| `RELATIVE_HUMIDITY` | `relativeHumidity` | **`Z_1_5M`** | **inferred** — height not documented; same screen instrument as temperature |
| `WIND_U` / `WIND_V` | `windSpeed`, `windDirection` | `Z_10M` | documented |
| `PRECIPITATION` | `qpf` | `Z_SURFACE` | |
| `CLOUD_COVER` | `cloudCover` | `Z_COLUMN` | total column, as Open-Meteo |

`Z_1_5M = AxisSpec(Interval(1.5, 1.5), AxisMode.POINT)` is added to `timeline.py` beside the existing
Z constants — the only change to a shared module.

**Probe.** `retrieve` → `_query` + `_parse`, exactly Open-Meteo's split.

```python
class TwcProbe:
    reports_units = False
    """TWC publishes no unit map; units are chosen by the request `units` param and never echoed.
    Canonical units are therefore parity-verified only (#41)."""

    def _query(self, *, longitude, latitude, over, variables) -> FetchRequest:
        # This vendor takes no window and no field selection: it returns its whole series with
        # every field. Both arguments are therefore unusable HERE - `variables` is still what
        # `_parse` slices by, so this is a query-builder fact, not a Probe-wide one.
        del over, variables
        return FetchRequest(
            path=f"/v3/wx/forecast/hourly/{self._duration}/enterprise",
            params={
                "geocode": f"{_fmt_coord(latitude)},{_fmt_coord(longitude)}",
                "units": "m",       # metric; km/h wind is finer than SI's integer m/s (fact 4)
                "language": "en-US",  # required by the vendor; no field we read is localized
                "format": "json",     # required; the only supported value
                "apiKey": self._api_key,
            },
        )
```

Three details that must not be "tidied" later:

- **`del over, variables` is scoped to `_query`.** `over` is unusable at all (no window parameter);
  `variables` is unusable *for the query* but is exactly what `_parse` slices the envelope by.
- **`language` and `format` are required by the vendor**, not optional niceties. `format=json` is the
  only supported value; `language` affects no field this leaf reads, so `en-US` is arbitrary-but-fixed.
- **`_fmt_coord` is duplicated from `open_meteo.py`, deliberately.** Vendor leaves must not import each
  other, and it is a one-line formatting helper. If a third leaf needs it, it graduates to
  `providers/base.py` — not before.

## Stages

### Stage 0 — capture a real response as the fixture — **DONE 2026-08-11**

**This stage existed because the envelope's exact nesting is the one vendor fact the documentation
does not pin.** The field *names* are documented; whether they sit at the top level or under a
container is not. Writing `_parse` against a guessed envelope and then discovering the real one is the
failure this avoided.

Run by the operator against the live key (which never reached this session) for **all seven
durations** at the pilot site, `units=m` — see [Confirmed by the live
capture](#confirmed-by-the-live-capture-2026-08-11-seven-durations-pilot). It answered more than
intended: the flat envelope, all seven `max_lead` values, the next-whole-hour start (⇒ 0119), the
per-tick expiry (⇒ fact 8 corrected), and the wind quantization premise.

**Remaining mechanical step:** land `hourly_10day.json` as the deterministic fixture, with the
`apiKey` absent from any recorded URL (the capture already scrubs it and refuses to save a body
containing the key).

**Until that step runs, the capture exists on one machine only** — it sits under `tmp/`, which
`.gitignore` excludes. Every declaration in this RFC, and the whole basis for `twc.py`, rests on it.
Losing it means re-running stage 0 against the metered key. Land the fixture before stage 1 rather
than alongside it.

### Stage 1 — the leaf *(red → green)*

`twc.py` with the module docstring (both doc links, the not-self-reported note), `_DURATIONS`, taps,
`TwcProbe`, `build`, `MANIFEST`; `Z_1_5M` added to `timeline.py`. Deterministic tests in
`tests/deterministic/nodes/providers/test_twc.py`, mirroring `test_open_meteo.py`:

- the six parameters decode from the captured fixture, at the right Z groups;
- the query carries all five required params, the right path for the offering, and `units=m`;
- wind decodes through the km/h→m/s conversion — a canned `windSpeed` of `36` yields `10.0` m/s,
  which is the one assertion that would catch a wrong `units` request;
- epoch `validTimeUtc` decodes to aware UTC and lands on the hourly step;
- a malformed envelope raises `RuntimeFailure`, not a bare `KeyError`;
- `build` rejects `cadence_hours` that is absent-and-defaulted (12), overridden (6), and invalid
  (`0`, `-1`, `"12"`, `True`) — the last four as `CompositionError`;
- `build` with `secret_value=None` raises `CompositionError`;
- **the declared availability window starts at the current hour, not the 12-hourly run anchor** —
  under a stopped clock at `13:30`, `capability.reach(pid)`'s T extent begins `13:00`, not `12:00`.
  This is the one declaration the first review got wrong, so it gets a test rather than a comment.
  It stands as written after the capture: the vendor's *first tick* under that clock would be
  `14:00`, but this test pins the **declaration**, and the one-hour over-declaration between them is
  exactly what [0119](../tickets/done/01-0119-live-window-edge-tolerance.md) absorbs. Do not "fix" this
  test to expect `14:00` — that would re-couple the declaration to delivery.

### Stage 2 — composition *(green)*

`server.py` registers `TWC_MANIFEST`. `config.py`: the priority pair flips (`twc=0`, `open-meteo=1`)
and the module docstring's "Open-Meteo primary, TWC fallback" flips with it. `Settings` gains two
fields, **both importing their defaults from `twc.py` so exactly one default exists**:

```python
twc_offering: str = twc.DEFAULT_OFFERING            # -> OfferingDef.name   (identity)
twc_cadence_hours: int = twc.DEFAULT_CADENCE_HOURS  # -> OfferingDef.settings (policy)
```

`Settings.offerings()` always emits `settings={"cadence_hours": self.twc_cadence_hours}`, so the value
is never implicit on the `Settings` path. `build`'s own `.get(..., DEFAULT_CADENCE_HOURS)` remains for
composers that construct an `OfferingDef` directly — that is its only role, and the shared constant is
what keeps the two from drifting.

`test_config.py`'s two `name="default"` pins update, and `test_twc_key_adds_fallback_offering` is
renamed — TWC is not the fallback any more.

New tests: **key-present composition succeeds** (closing the `unknown impl` boot trap), **an unknown
`twc_offering` fails at boot** with `CompositionError` (the payoff of identity-as-name), **TWC wins by
default** with both producers enabled, and Open-Meteo still admits the same parameters.

Also here: the ticket's sweep criterion — **no `Visual Crossing` reference remains** in `src/`,
`tests/`, or live `docs/` (history, `tickets/done/`, `rfc/done/`, and the product-roadmap plugin menu
excepted). Verify by grep; the 2026-08-08 align swept prose already, so this is confirmation.

### Stage 3 — the import-direction guard — **nothing to write** *(corrected 2026-08-11)*

An earlier draft called for building this guard, and cited the edge record as listing it unguarded.
Both were wrong. **It already exists**:
[test_probe_seam_guard.py](../../tests/deterministic/test_probe_seam_guard.py) discovers vendor
modules by globbing `providers/*.py` minus a shared set, so `twc.py` is covered the moment it is
created, with nothing added. [edge/provider.md](../edge/provider.md) cites it as the validating
artifact.

It also already solves the nuance this stage raised — that a module-level scan "would fail Open-Meteo
too", since `build` legitimately takes a `Clock`. The shipped guard splits it: `_BUILD_FACE_ONLY =
{"Clock"}` exempts the composition face at module level, while a second test walks the `*Probe` class
bodies and forbids `Clock` there too. `Interval` is correctly not forbidden.

**Do not add a second guard.** The one thing to confirm is that `twc.py` is not accidentally added to
`_SHARED`.

### Stage 4 — parity *(green; not run by default)*

`tests/parity/readers/twc.py` — independent reader, no meteoscape imports (the existing reader guard
covers it automatically), key from `METEOSCAPE_TWC_API_KEY`. `tests/parity/test_twc.py` mirroring
`test_open_meteo.py`, composing with `Settings(open_meteo_enabled=False)` so TWC is unambiguously the
producer under test, and **skipping with a clear message when the key is absent** — Open-Meteo needs no
such guard, so this is new. `settings.secrets()` is passed to `write_evidence` and `format_summary`,
which scrubs the `apiKey` from the recorded URL (fact 8).

Tolerances mirror Open-Meteo's `SPEC`, and the vendor's declared types make that sound: `temperature`
and `qpf` are Decimal, `relativeHumidity` / `cloudCover` / `windDirection` / `windSpeed` are Integer —
both sides read the same numbers, so `Exact()` holds for the four non-wind parameters. Wind keeps
`Absolute` / `Circular` tolerances because u/v round-trips through trigonometry **and** through the
km/h→m/s conversion, which the reference reader performs independently.

### Stage 5 — the single live run *(the ticket's verification moment)*

`uv run pytest tests/parity -k twc`, once, by hand.

**Stage 0 already answered most of what this stage was for** — `max_lead` per offering (all seven
exact), the series start (next whole hour), the wind quantization (integer km/h), and the refresh
question (fact 8: ~5 min head, ~21 min tail, so the payload certainly changes within 12 h; Δ stays a
deliberate under-poll, decided at [What `expiration` promises](#what-expiration-promises)).

What remains genuinely for the live run:

- **value agreement** against the independent reference reader — the actual parity question, and the
  only guard on `units=m` being what we think it is (fact 5: the vendor reports no units, so a wrong
  `units` request would silently divide wind by 3.6);
- the **licensed duration** actually served under the operator's key;
- confirmation that the fixture's shape still holds against a live fetch, since stage 1 is written
  against a single captured payload.

### Stage 6 — records *(green)*

Tick the ticket's criteria and move it to `done/`; update the delivery status row and the capability
table (second provider now configured); note in [edge/provider.md](../edge/provider.md) that the
shape/vendor split survived its first real test — **or, if it did not, record precisely what had to be
written outside the Probe**, which the ticket names as its most valuable possible finding.

## Limitations and follow-ups

- **The vendor's per-tick `expirationTimeUtc` is recorded but unused** (fact 8). Adopting it needs
  `expiration`'s two roles — caller staleness bound and Reservoir refetch trigger — split first, or
  the refetch interval collapses to ~5 minutes. → [ideas: freshness](../ideas.md#freshness),
  [#18](../concerns.md#18-clock-anchored-footprint-fidelity); wanted by the faster-nowcast case, not
  by v1.
- **The two-tier expiry suggests two models behind one endpoint** — the ~5-minute head is exactly the
  `6hour` horizon. If that holds, `hourly_6hour` may be a genuinely fresher product than a crop of
  `hourly_10day`, which would matter to offering-aware selection →
  [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection). One capture
  is not enough to claim it.
- **`publication_latency` stays provisional** past this ticket if the live run cannot settle it; it
  must remain marked in the source either way.
- **Δ is a polling interval, not a run cadence** → [#18](../concerns.md#18-clock-anchored-footprint-fidelity).
  Run identity is only as real as the vendor's published schedule, and TWC publishes none. Its
  epoch-anchored `expiration` also makes the **effective** interval ≈ Δ/2, so the meter will read about
  double the naive expectation.
- **`relativeHumidity`'s Z is inferred**, and parity structurally cannot verify a declared height
  ([edge/provider.md](../edge/provider.md)).
- **Tick semantics are untouched** → [#48](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick) /
  [0126](../tickets/01-0126-tick-convention-declaration.md). TWC matches the lattice; Open-Meteo does
  not.
- **Nothing enforces that the parity check runs** → [#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).
  By decision, this ticket runs it once by hand.
- **Fall-through does not exist**, so a TWC 429 or quota exhaustion fails the whole request →
  [004](../tickets/01-0121-second-provider-fallback.md). A *shorter reach* is not this case: reach
  differences resolve by admission.
- **Two offerings of one impl may both be enabled**, and the Arbiter would rank between them →
  [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection). Left unguarded.
- **The wider TWC licence** (≈80 products: indices, observations, raster) is roadmap work in several
  differently-shaped steps → [product-roadmap Phase 2](../product-roadmap.md).
