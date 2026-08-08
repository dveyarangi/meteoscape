# TWC provider

**Legacy id:** 011

- **Status:** Ready
- **Depends on:** [m4 — Snapped request mode](./done/01-0100-snapped-t-request-mode.md) (done —
  `TimelineProvider` is extracted; this ticket writes only a Probe behind it),
  [m3 — Provider parity checks](./done/01-0080-provider-parity-checks.md) (the harness this Probe's check
  plugs into)
- **Blocks:** [004 — Second-provider fallback](./01-0150-second-provider-fallback.md) (needs a real second
  producer to fall back *to*), [008 — Config, secrets, degradation](./01-0180-config-secrets-degrade.md)
  (needs a shipped manifest that actually declares a secret)
- **Outcome:** TWC shipped as the second producer — a `TimelineProbe`, a manifest declaring
  the first real `SecretSlot`, its live parity check.

> **Provider identity history.** Planned as TWC from the start; swapped to Visual Crossing at the
> 2026-08-02 align because TWC access was unverified and any keyed provider satisfies the secrets
> seam; **reverted to TWC at the 2026-08-08 align** — TWC access is now verified in production use,
> dissolving the swap's premise, and TWC is the vendor the first real deployment runs, so its parity
> evidence matters. The code ([`config.py`](../../src/meteoscape/config.py)) kept the `twc` names
> throughout — the Visual Crossing sweep never started, so reverting deletes work rather than redoing
> it. Visual Crossing remains a future-plugin candidate (generous free tier — the reproducible choice
> for outside adopters) in [product-roadmap](../product-roadmap.md).

## Parent PRD

`docs/v1-requirements.md`

## Why this is its own ticket

Split out of [004](./01-0150-second-provider-fallback.md) at the 2026-08-02 align. The two halves are
tested differently and fail differently: **this** ticket is *"does one vendor's data arrive correctly"*
— answered by a live parity check against the real API, with its own key, quota, and evidence; **004**
is *"does the Arbiter select and fall back correctly"* — answered deterministically against mocked
transports, with no network at all. Bundling them would put a live-network dependency inside the
fallback proof and make a vendor outage look like a fallback regression.

It is also the first real test of m4's [shape/vendor split](../edge/provider.md): if adding a producer
of a known shape requires anything beyond a Probe and its declarations, that abstraction is wrong, and
this ticket is where we find out.

## What to build

**1. The Probe.** `TwcProbe` implementing `TimelineProbe` — one query builder, one envelope
parse, a tap table, and a `CadenceDef`. TWC's hourly forecast endpoint is point-plus-series, the **same
shape as Open-Meteo**, so this adds **no wrapper**. It must contain no algebra: no `ground`, no
`agreed_geometry`, no crop, no provenance stamping, no `Clock`, no `Coverage` construction — those are
`TimelineProvider`'s, and reaching for them is the [edge record](../edge/provider.md)'s
import-direction violation.

**2. Manifest and catalogue registration.** `ProviderManifest` with `secret=SecretSlot(...)` — the
first shipped manifest to declare one — registered in `PROVIDER_CATALOG`.

**3. Code is already named for TWC.** [`config.py`](../../src/meteoscape/config.py) carries
`twc_api_key`, the `OfferingDef(impl="twc", …, secret_ref="twc_api_key")`, and the "Open-Meteo
primary, TWC fallback" docstring, with `test_config.py` pinning those names — all stay. Prose was
swept back to TWC at the 2026-08-08 align; **verify, don't assume:** re-grep `docs/` for stray
`Visual Crossing` references outside `sessions/`, `tickets/done/`, `rfc/done/`, and
product-roadmap's plugin menu (history stays as written).

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
- [ ] **The Probe adds no wrapper and no algebra.** Snapped resolution, unit conversion, `decode`, Z
      grouping, and the crop all arrive by declaration. If any must be written here, m4's abstraction
      is wrong and that is this ticket's most valuable finding — record it rather than working around
      it.
- [ ] An import-direction test pins that the Probe module touches no manifold types (`Domain`,
      `Selection`, `Coverage`, `Capability`, `Provenance`, `Clock`) — the guard the
      [edge record](../edge/provider.md) lists as **⚠ unguarded**.
- [ ] The manifest declares a `SecretSlot`; the key is injected via config at construction and reaches
      `build`. No secret appears in fixtures, logs, or parity evidence.
- [ ] **Key-present composition succeeds** — the `unknown impl` trap is closed and pinned by a test.
- [ ] Key-absent still degrades gracefully: the server starts and serves on Open-Meteo alone
      ([008](./01-0180-config-secrets-degrade.md) owns the wider config story).
- [ ] **Unit self-reporting is declared honestly.** TWC selects units via a request parameter
      (`units`); confirm whether its payload reports per-field units. If it does not, the Probe
      declares that it does **not** self-report and the record's consequence applies — canonical units
      become **parity-verified only** for this provider
      ([#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted)). Echoing the declared units
      back would be a fabricated confirmation.
- [ ] No `Visual Crossing` reference remains in `src/`, `tests/`, or live `docs/` (history and the
      product-roadmap plugin menu excepted).
- [ ] TWC ships and passes its live parity check
      (`uv run pytest tests/parity -k twc`), with the reference reader importing no
      Meteoscape code (existing guard covers it with no registration).

## User stories addressed

- User story 12 (key injected via config), user story 13 (absent key degrades gracefully) — jointly
  with [008](./01-0180-config-secrets-degrade.md).
