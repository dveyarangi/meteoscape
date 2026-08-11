# TWC provider

**Legacy id:** 011

- **Status:** Ready
- **Plan:** [TWC provider RFC](../rfc/01-0120-twc-provider.md) — enterprise endpoints,
  seven offering rows, `units=m`, 12 h polling cadence.
- **Depends on:** [m4 — Snapped request mode](./done/01-0100-snapped-t-request-mode.md) (done —
  `TimelineProvider` is extracted; this ticket writes only a Probe behind it),
  [m3 — Provider parity checks](./done/01-0080-provider-parity-checks.md) (the harness this Probe's check
  plugs into),
  [0119 — live-window edge tolerance](./01-0119-live-window-edge-tolerance.md) (**added 2026-08-11**
  after the stage 0 capture: TWC's series starts at the next whole hour, so without 0119 the refill
  gate never reaches containment and every request costs one metered vendor call)
- **Blocks:** [004 — Second-provider fallback](./01-0121-second-provider-fallback.md) (needs a real second
  producer to fall back *to*), [008 — Config, secrets, degradation](./01-0123-config-secrets-degrade.md)
  (needs a shipped manifest that actually declares a secret)
- **Outcome:** TWC shipped as the **primary** producer — a `TimelineProbe`, a manifest declaring the
  first real `SecretSlot` and one offering row per licensed duration, its live parity check, and the
  priority flip that puts it ahead of Open-Meteo.

## What changes because TWC is primary

- **Parity remains manual.** The TWC parity check guards the default path, but `tests/parity` stays
  outside CI and CI holds no key. Run it once after landing; scheduling and coverage enforcement stay
  at [#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).
- **Key-absent is the degraded mode.** Without the TWC key, composition omits the primary and serves
  on Open-Meteo → [008](./01-0123-config-secrets-degrade.md).
- **Fault fall-through is separate.** A TWC 429 or exhausted quota is a `runtime-failure`, which the
  current Arbiter propagates for the whole request → [004](./01-0121-second-provider-fallback.md).
  A shorter reach is not fall-through: reach differences between
  producers are resolved by **admission**, not fallback: a request beyond TWC's declared reach simply
  does not admit TWC, and Open-Meteo wins on capability
  ([ADR-0004](../adr/0004-producer-resolution-and-capability.md)). A window spanning both reaches still resolves whole to one
  producer — `agreed_geometry` answers one bounded geometry, per
  [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection).
- **Vendor spend becomes real** → [vendor-call ledger](./02-0124-vendor-call-ledger.md).
- **No new unit-conversion edge.** The Probe requests `units=m`; wind reuses Open-Meteo's inline
  `km/h → m/s` conversion, so [010](./01-0122-unit-conversion-edge.md)'s catalogue trigger remains
  unmet. Metric is preferred over SI because TWC's integer wind field yields 0.28 m/s rather than
  1 m/s quantization. TWC does not self-report units, so parity is the only guard on that declaration.

## Parent PRD

`docs/v1-requirements.md`

## Why this is its own ticket

This ticket and [004](./01-0121-second-provider-fallback.md) are tested differently and fail
differently: **this** ticket is *"does one vendor's data arrive correctly"*
— answered by a live parity check against the real API, with its own key, quota, and evidence; **004**
is *"does the Arbiter select and fall back correctly"* — answered deterministically against mocked
transports, with no network at all. Bundling them would put a live-network dependency inside the
fallback proof and make a vendor outage look like a fallback regression.

It is also the first real test of m4's [shape/vendor split](../edge/provider.md): if adding a producer
of a known shape requires anything beyond a Probe and its declarations, that abstraction is wrong, and
this ticket is where we find out.

## What to build

> **Vendor facts** ([TWC v3 hourly forecast](https://developer.weather.com/docs/openapi/hourly-forecast-3-0)).
>
> | | Open-Meteo (shipped) | TWC v3 hourly |
> |---|---|---|
> | path | `/v1/forecast` | `/v3/wx/forecast/hourly/{duration}/enterprise` — **duration in the path** |
> | auth | none | `apiKey` **as a query parameter** |
> | location | `latitude` + `longitude` | `geocode=lat,lon` |
> | required params | `latitude`, `longitude`, `hourly`, `start_hour`, `end_hour`, `timezone` | `geocode`, `units`, **`language`**, **`format`**, `apiKey` — all five required; there is **no window parameter**, so the vendor decides the span |
> | time | ISO strings | `validTimeUtc` — **UNIX epoch** |
> | fields | `temperature_2m`, … | `temperature`, `relativeHumidity`, `qpf`, `cloudCover`, `windSpeed`, `windDirection` |
> | units | `hourly_units` echoed per field | **not reported at all** — chosen only by the request `units` param (`e`/`m`/`h`/`s`) |
>
> TWC does not self-report units. The Probe declares that fact; canonical units are
> **parity-verified only** for this provider.
>
> The shape holds — point-plus-columnar-series, the Open-Meteo family — so **no wrapper**. The
> differences (epoch time, `qpf`, key-in-query) are query-builder and tap-table detail.
>
> **TWC takes no window parameter**, so `TwcProbe.retrieve` receives `over` and **cannot use it**: the
> vendor returns its whole series and the wrapper crops. That is the leaf's *natural fetch unit* on the
> T axis — already the architecture's position (*ask narrow, answer natural*,
> [edge/provider.md](../edge/provider.md)) — and `_lattice_of` builds the axis from the ticks actually
> delivered, so a wider-than-asked answer is normal, not a fault.
>
> **This raises the stakes on the Shelf declaration** — the declared window governs **admission**, and the
> vendor governs what exists. ~~So the declared window must never begin before the series: hence
> **`1h`**, not `None`.~~ **Resolved 2026-08-11 (align), after the stage 0 capture showed no Shelf value
> can satisfy that rule:** TWC's series begins at the **next** whole hour, while `valid_time` can only
> *floor* ([cadence.py:31](../../src/meteoscape/manifold/cadence.py)) — so `now` itself always sits in
> a declared-but-undelivered gap.
>
> The premise that a declaration must match delivery exactly is what gave way. A live window is an
> **estimate**; holdings are the truth; and the declared axis itself decides whether a refetch would
> add anything — for a rolling window, satisfied once its horizon reaches the ask's start. That rule
> is [0119](./01-0119-live-window-edge-tolerance.md), landing ahead of this ticket, and it is
> vendor-agnostic rather than a per-vendor declaration knob.
>
> **The hourly Shelf (`shelf=1h`) therefore stands** — not because it is exact, but because **declaring late is
> the safe direction** and `1h` keeps the over-declaration to at most one hour, where `None` would
> anchor on the 12-hourly run grid and reach up to 13 hours backwards.
>
> What 0119 repairs, in this vendor's shape: the refill gate compares the request against the
> **declared** reach ([reservoir.py:113](../../src/meteoscape/nodes/reservoir.py)) and then asks
> whether **holdings** contain it ([:135](../../src/meteoscape/nodes/reservoir.py)) — never true here,
> so every request refills, at one metered call each. A request lying wholly in the gap additionally
> faults at [:177](../../src/meteoscape/nodes/reservoir.py). A *straddling* request already serves
> correctly, because `ground` asks the record's own axis to clip itself. Family, not identity, with
> [#21](../concerns.md#21-serves-extent-vs-project-crop-ability).

> **Duration is an offering, not a setting.** The licensed duration is a **path
> segment**, and the catalogue declares **one `OfferingSpec` per duration**; the operator selects one
> with `OfferingDef(impl="twc", name=…)`. `spec.name` already reaches `build`
> ([composition.py:94](../../src/meteoscape/nodes/composition.py)), so this needs no new plumbing.
>
> **The product is *Hourly Forecast — Enterprise*** (the licence held), whose path carries the
> duration as a segment and `enterprise` as a suffix:
>
> ```
> https://api.weather.com/v3/wx/forecast/hourly/{6hour|12hour|1day|2day|3day|10day|15day}/enterprise
> ```
>
> **All seven durations become offering rows** — `hourly_6hour`, `hourly_12hour`, `hourly_1day`,
> `hourly_2day`, `hourly_3day`, `hourly_10day`, `hourly_15day` — because the licence covers them and
> the operator must be able to pick any. **`hourly_10day` is the default**; the rest exist so
> switching is a config change, not a code change.
>
> The *standard* Hourly Forecast product (`/hourly/2day`, `/hourly/15day`, no `enterprise` suffix) is
> a separate endpoint set and would be a separate implementation.
>
> Duration belongs in `OfferingDef.name`, not `OfferingDef.settings`, because each product declares
> its **own reach**, and
> `SourceKey.dataset` then records which extent answered. A wrong offering name is a boot
> `CompositionError` from the binder; a wrong duration string would have been a runtime 404 — the same
> shape of trap acceptance criterion 6 exists to close.
>
> First offering-parameterized producer, so this lands part of
> [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)'s leaf side.
> Its sharpest worry there — *two offerings of one impl fetching identical payloads under distinct
> `SourceKey`s* — **does not apply**: the duration is in the path, so the payloads genuinely differ.
> That is the vendor token #20 records as missing. Nothing stops an operator enabling both durations
> at once; left unguarded, since #20 owns offering-aware selection.

> **Cadence declaration.** TWC documents neither refresh cadence nor whether the series is hour- or
> day-anchored. Policy values are explicit; delivery-dependent values remain provisional and are
> confirmed against the live key during the manual parity run:
>
> | | value | why |
> |---|---|---|
> | `cadence` | **`12h`, operator-overridable** | Polling policy against a monthly allotment; faster nowcasting may choose differently. **The vendor's own refresh is ~5 min (near-term) / ~21 min (tail)** — see below; 12 h is a deliberate under-poll, not an estimate of the vendor. |
> | `publication_latency` | **`0`** | The bucket regime has no run-publication delay → [ADR-0003](../adr/0003-provenance-and-origin.md#run-and-bucket-regimes). |
> | `max_lead` | from the selected offering | ✅ **Confirmed 2026-08-11** for all seven durations: 5/11/23/47/71/239/359 h, uniform hourly steps. |
> | `shelf` | **`1h`** | ✅ Delivery is **hour**-anchored, and starts at the *next* whole hour — so `1h` over-declares by up to an hour, absorbed by [0119](./01-0119-live-window-edge-tolerance.md). Declaring late is the safe direction. |
>
> **`cadence` is not a vendor fact and must not be "corrected" to one.** The payload carries a
> per-tick `expirationTimeUtc` (first 7 ticks ~5 min out, the remaining 233 ~21 min out). We do not
> adopt it: `expiration` is *also* the Reservoir's refetch trigger
> ([reservoir.py:138](../../src/meteoscape/nodes/reservoir.py)), so adopting a 5-minute expiry would
> set our polling to 5 minutes and spend the allotment 12 h exists to conserve. `exp` at the MCP edge
> promises *our* refresh policy, not the vendor's. Recorded as a known-unused signal →
> [ideas: freshness](../ideas.md#freshness), [#18](../concerns.md#18-clock-anchored-footprint-fidelity).
>
> TWC uses ADR-0003's **bucket regime** because it publishes no run schedule. The source must name
> that declaration; [#18](../concerns.md#18-clock-anchored-footprint-fidelity) owns the anchored-expiry
> cost and provider-real freshness escape.

> **Cadence is operator policy.** It rides `OfferingDef.settings`; TWC's `build` reads
> `cadence_hours`, integer, default
> **12**, validated there with `CompositionError` on a non-positive or non-integer value.
>
> Live parity must verify the provisional delivery facts: plausible values alone do not prove that
> the declared window matches the vendor series.

**1. The Probe.** `TwcProbe` implementing `TimelineProbe` — one query builder, one envelope
parse, a tap table, and a `CadenceDef`. TWC's hourly forecast endpoint is point-plus-series, the **same
shape as Open-Meteo**, so this adds **no wrapper**. It must contain no algebra: no `ground`, no
`agreed_geometry`, no crop, no provenance stamping, no `Clock`, no `Coverage` construction — those are
`TimelineProvider`'s, and reaching for them is the [edge record](../edge/provider.md)'s
import-direction violation.

**2. Manifest and catalogue registration.** `ProviderManifest` with `secret=SecretSlot(...)` — the
first shipped manifest to declare one — registered in `PROVIDER_CATALOG`, carrying one `OfferingSpec`
per enterprise duration.

**2b. Cite the vendor documentation in the leaf's module docstring.** Two links: the **portfolio**
(the product map, `https://docs.google.com/document/d/1pXDXkT4wd4I77LxkBnltQ7tKG4GlOsDeRUPdaDDtAW8`)
and the **enterprise hourly endpoint** (`https://twcapi.co/v3FODHE`), which is where every declaration
below the docstring — paths, required params, field names, units, `qpf`'s window, the 1.5 m
temperature height — comes from. The leaf is the right home because
[edge/provider.md](../edge/provider.md) puts vendor knowledge there and the tap table is the thing
derived from those pages; no dedicated vendor-reference doc, which the
[doc map](../README.md) has no row for. Note in the docstring that both are Google Docs behind
`twcapi.co` shortlinks, and that **units are not self-reported** — so those pages, not the payload,
are the only evidence for what the numbers mean.

**3. Config and priority.**
[`config.py`](../../src/meteoscape/config.py) carries `twc_api_key` and the
`OfferingDef(impl="twc", …, secret_ref="twc_api_key")`, with `test_config.py` pinning those names —
the key and `secret_ref` stay. Three things change:

- the **priority pair** (`twc=0`, `open-meteo=1`);
- the module docstring's producer ordering;
- the **offering name**. Today `Settings.offerings()` emits `name="default"`, which under the
  offering-per-duration decision is not a catalogue row at all. `Settings` gains a field naming the
  licensed offering (defaulting to `hourly_10day`), and that value becomes `OfferingDef.name`. This
  is where the decision pays: a wrong value is a boot `CompositionError` from the binder resolving
  the name against `PROVIDER_CATALOG`, not a runtime 404 from the vendor.

`test_config.py` pins `name="default"` in two tests, both of which update, and
`test_twc_key_adds_fallback_offering` is renamed once TWC is primary.

**4. Closes a live trap.** `impl="twc"` is not in `PROVIDER_CATALOG`, so an operator setting the key
today emits an offering the binder cannot resolve and gets a boot `CompositionError: unknown impl` —
not a fallback provider, and not graceful degrade. Registering a real impl behind a real key closes it;
a test should pin key-present composition succeeding.

**5. Its parity check** — reader, live test, deterministic `parse_reference` coverage, per the
[edge record](../edge/provider.md)'s contribution bundle. The live check runs under an
operator-supplied key; no key or evidence artifact may expose the secret.

## Acceptance criteria

- [ ] `TwcProbe` serves the canonical parameters it declares, exercised through
      `TimelineProvider` with a **mocked transport** in the deterministic suite.
- [ ] **TWC wins by default.** With both producers enabled, every canonical parameter resolves to
      TWC; a test pins the priority pair rather than trusting the integers to stay put. Open-Meteo
      remains configured and admits the same parameters — it is the backstop
      [004](./01-0121-second-provider-fallback.md) makes live, not a disabled producer.
- [ ] **The Probe adds no wrapper and no algebra.** Snapped resolution, unit conversion, `decode`, Z
      grouping, and the crop all arrive by declaration. If any must be written here, m4's abstraction
      is wrong and that is this ticket's most valuable finding — record it rather than working around
      it.
- [ ] The existing Probe import-direction guard covers the TWC module: no `Domain`, `Selection`,
      `Coverage`, `Capability`, `Provenance`, or `Clock` imports.
- [ ] The manifest declares a `SecretSlot`; the key is injected via config at construction and reaches
      `build`. No secret appears in fixtures, logs, or parity evidence.
- [ ] **Key-present composition succeeds** — the `unknown impl` trap is closed and pinned by a test.
- [ ] Key-absent still degrades gracefully: the server starts and serves on Open-Meteo alone
      ([008](./01-0123-config-secrets-degrade.md) owns the wider config story).
- [ ] **Unit self-reporting is declared honestly.** TWC does not report per-field units; the Probe
      declares that fact, and the record's consequence applies:
      canonical units are **parity-verified only** for this provider
      ([#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted)).
- [x] ~~The source marks delivery-dependent cadence facts provisional; the manual parity run confirms
      the first tick, series length, and whether the availability window shifts hourly or daily.~~
      **Answered by the stage 0 capture, 2026-08-11**, ahead of parity: hour-anchored, series starts
      at the *next* whole hour, and all seven `max_lead` values confirmed exact (5/11/23/47/71/239/359 h).
      What stays provisional is `publication_latency` alone; `cadence` is policy, not a vendor fact.
- [ ] TWC ships and passes its live parity check
      (`uv run pytest tests/parity -k twc`), with the reference reader importing no
      Meteoscape code (existing guard covers it with no registration).

## User stories addressed

- User story 12 (key injected via config), user story 13 (absent key degrades gracefully) — jointly
  with [008](./01-0123-config-secrets-degrade.md).
