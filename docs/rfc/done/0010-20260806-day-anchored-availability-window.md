# RFC 0010 · 2026-08-06 · Day-anchored availability window — implementation plan

Implementation plan for [day-anchored availability window](../../tickets/done/01-0112-day-anchored-availability-window.md).
The *why* — the probed vendor shape, the rejected alternatives (max_lead cut; probe-side clamp) —
is the ticket's; this plan is the single way to build it.

**Scope in one line:** `CadenceDef` gains an optional **`window_quantum`** that anchors
`valid_time` at `floor(now, quantum)` instead of the run anchor; Open-Meteo declares
`{quantum 24 h, max_lead 383 h}`; narration floors to whole days; nothing else in the engine,
edge, or Probe changes.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `CadenceDef` / `RollingAxis` (`manifold/cadence.py`) | [ADR-0003 §cadence](../../adr/0003-provenance-and-origin.md#run-identity--freshness--the-cadence) | The one widening: `window_quantum: timedelta \| None = None`; `valid_time` branches on it. `anchor`, `expiration`, `RollingAxis` untouched. ADR-0003 amended at landing (stage 4). |
| Open-Meteo declaration (`nodes/providers/open_meteo.py`) | [edge/provider.md](../../edge/provider.md) | `CADENCE` declares the probed truth: `window_quantum=24 h`, `max_lead=383 h`; `cadence`/`publication_latency` stay 1 h / 1 h. |
| Narration (`api/mcp_app.py`, `_horizon_sentence`) | [edge/mcp.md](../../edge/mcp.md) | One formula change: whole-days **floor** replaces the `% 24 == 0` branch. No other edge change. |
| Provenance / freshness | ADR-0003 | **Untouched** — `issue_time = anchor(now)`, `expiration = A + Δ + L` keep reading the run clock ([timeline.py](../../../src/meteoscape/nodes/providers/timeline.py) lines 217–219 are the only consumers; verified 2026-08-06). |
| Admission / `ground` / `clip` | ADR-0002/0004 | **Untouched** — they read `extent`/`valid_time`; the truthful window flows through existing code. |
| Probe seam | [edge/provider.md](../../edge/provider.md) | **Untouched** — the Probe stays clock-free; the fix is precisely *not* a vendor-face clamp. |

## Facts that shape the implementation (verified 2026-08-06)

1. **The vendor's availability, live-probed:** `end_hour = today00+16d−1h` → 200,
   `today00+16d` → 400 (upper edge is midnight-quantized, exclusive at +16 d);
   `start_hour` back to ~92 days → 200 (archive-deep lower edge — out of scope, recorded at
   [#18](../../concerns.md#18-clock-anchored-footprint-fidelity) as residue). Single-tick ask at the
   last hour → 200.
2. **`CadenceDef` consumers are exactly three**: `valid_time` (the footprint window — the thing
   being fixed), `anchor` (provenance `issue_time`), `expiration` (freshness) —
   [timeline.py:217–219](../../../src/meteoscape/nodes/providers/timeline.py) and
   `RollingAxis.extent`. Nothing else reads it, so anchoring the window on its own clock cannot
   perturb run identity or freshness.
3. **`RollingAxis.clip` materializes `(upper − lower) // step + 1` ticks from `window.lower`.**
   With `[today00, today00 + 383 h]` that is 384 hourly cells — exactly the vendor's 16 calendar
   days. This is why `max_lead` becomes **383 h**, not 16 d: `max_lead` is the window's *inclusive
   upper offset* (the last servable lead). Subtracting a step inside `valid_time` instead would
   put series-step knowledge into `CadenceDef`, which deliberately does not own the step
   ([RFC 0009](./0009-20260725-m4-snapped-t-request-mode.md) decision 8).
4. **The leaf tests read the window dynamically** (`CADENCE.valid_time(STOPPED.now())` — e.g. the
   straddle test) or use interior bounds, so they survive the declaration change; only their
   prose comments name `11:00` / `[11:00, +16d]` and get swept. The **e2e absolute pins** are the
   behavior-coupled sites: the default-window case (384 → 372 under the noon clock) and the
   out-of-range fetch (`start_hour` `11:00` → `00:00`).
5. **The fakes stay run-anchored.** `fakes._CADENCE` omits the quantum, so every existing
   cadence/domain/mcp test keeps its shape; the narration floor leaves 168 h at "7 days".
6. **The narration mechanism survives; only the formula changes.** The extent length is still
   clock-invariant (383 h, whatever the hour), and "out to 15 days ahead of the latest model run"
   is *guaranteed* true: `window.upper − run-anchor ≥ 15 d 1 h` at every hour for the day-anchored
   window, and exactly 7 d for the run-anchored fakes. The ≤ 23 h understatement is the accepted
   trade (user-accepted 2026-08-06; the exact sentence becomes narration's business again at the
   open-ended flip, owned by the [retentive-store ticket](../../tickets/done/01-0115-retentive-store-freshness.md)'s
   align).
7. **The default request under the e2e noon clock serves 372 ticks**: bounds
   `[Jul 11 12:00, reach end Jul 26 23:00]` on the hourly lattice — `24·16 − 12 = 372` (the
   `12` is the stopped clock's hours-into-day). Tests derive counts from `CADENCE` + the clock,
   never bare numbers.
8. **Two-fetch divergence is neither created nor removed.** The race window moves from every hour
   boundary to the midnight boundary (a request in flight across 00:00 UTC can straddle two
   windows); the judgement and ownership recorded at 003c
   ([#30](../../concerns.md#30-response-membership-under-runtime-degraded-fallback), retention next)
   carry over unchanged.

## Design decisions

1. **The widening is a quantum, not a second anchor.** `window_quantum: timedelta | None = None`
   on `CadenceDef`; `valid_time` becomes:

   ```python
   def valid_time(self, now: datetime) -> Interval[datetime]:
       """The availability window: `[W, W + max_lead]`, `W = floor(now, window_quantum)` when a
       quantum is declared (a shelf-anchored product — e.g. a by-calendar-day vendor), else the
       run anchor (the run's own forecast window). Two clocks: the run clock keeps identity and
       freshness; the quantum, when present, anchors only what is *servable*."""
       base = floor_to(now, self.window_quantum) if self.window_quantum else self.anchor(now)
       return Interval(lower=base, upper=base + self.max_lead)
   ```

   Named `window_quantum` (not `window_anchor`) because "anchor" names *instants* throughout this
   codebase (`CadenceDef.anchor()`, `RegularAxis.anchor`) and this is a timedelta the window
   snaps to. No latency shift on the shelf clock: the vendor's day product exists from midnight
   regardless of run publication — that is what makes it a different clock.
2. **Open-Meteo declares the probed truth**:

   ```python
   CADENCE = CadenceDef(
       cadence=timedelta(hours=1),
       publication_latency=timedelta(hours=1),
       # The availability shelf: 16 calendar days of hourly ticks, [today00, today00+15d23h].
       # Probed 2026-08-06: end_hour today00+16d → HTTP 400; today00+16d−1h → 200 (RFC 0010).
       max_lead=timedelta(hours=383),
       window_quantum=timedelta(hours=24),
   )
   ```

3. **Narration floors to whole days.** In `_horizon_sentence`, the span rule becomes: `days =
   hours // 24`; narrate `f"{days} days"` when `days >= 1`, else `f"{hours} hours"` — the
   `% 24 == 0` branch is deleted. Production: 383 h → "15 days"; fakes: 168 h → "7 days"
   (unchanged); a sub-day reach still narrates hours. Sentence text unchanged
   ("out to {span} ahead of the latest model run" — guaranteed true, fact 6).
4. **Nothing else moves.** No edge change beyond the formula, no `RollingAxis` change, no Probe
   change, no new error paths: the truthful window flows through `clip`/`ground`/admission as
   built. The archive-deep lower edge and the open-ended request member are explicitly **not**
   built here (ticket's criteria route them to #18 and the retentive-store align).

## Flows

Unchanged from 003c. The only behavioral deltas, all caused by the window now being
`[today00, today00+383h]`: the omitted-`end` default resolves to `bounds ∩` that window (never a
vendor 400); an explicit `start` earlier today is inside the window and serves; an explicit window
in yesterday-or-older stays `capability-mismatch` (admission, as today). Failure surface:
unchanged.

## Implementation stages

Each stage ends with `uv run ruff check . && uv run ruff format --check . && uv run pyright &&
uv run pytest` green.

1. **`window_quantum`** — RED (`tests/deterministic/manifold/test_cadence.py`): a day-quantum
   `CadenceDef` under a mid-day `StoppedClock` yields `valid_time = [midnight, midnight + max_lead]`;
   advancing the clock within the day moves nothing; crossing midnight jumps the window by a whole
   day (`_AdvancingClock` pattern); `anchor` and `expiration` are **unaffected by the quantum**
   (same values with and without it — the two-clocks pin); a quantum-less `CadenceDef` is
   byte-identical to today (existing tests are that pin; one explicit `None` case for totality).
   GREEN: the field + the `valid_time` branch (decision 1).
2. **Narration floor** — RED (`test_mcp_app.py`): a 383 h-reach fake (a `CadenceDef` with
   `max_lead=383 h`, `window_quantum=24 h` through `fakes.footprint_domain(cadence=…)`) narrates
   "out to 15 days ahead of the latest model run"; the standard fake still narrates "7 days"; a
   sub-day fake (e.g. `max_lead=18 h`) narrates "18 hours". GREEN: the floor rule (decision 3).
3. **The Open-Meteo declaration + its dependent pins** — flip `CADENCE` (decision 2). Same stage,
   named so none is discovered mid-stage:
   - Leaf tests (`test_open_meteo.py`): assertions reading `CADENCE.valid_time` survive; the
     prose comments naming `11:00` / `[11:00, +16d]` are swept to the day-anchored truth.
   - e2e `test_forecast_hourly_default_window_is_the_full_reach`: 384 → **372** ticks
     (`_canned_forecast(hours=372)`; derivation comment `24·16 − 12 = 372`, fact 7);
     `valid_time[-1]` → `2026-07-26T23:00:00Z`; the narration assert → "out to 15 days".
   - e2e `test_out_of_range_bounds_fetch_exactly_the_clipped_window`: captured
     `start_hour` → `"2026-07-11T00:00"`, `end_hour` → `"2026-07-26T23:00"`; `_canned_forecast`
     gains an optional `start: datetime` (default unchanged, so no other caller moves) and this
     test cans `start=midnight, hours=408` so delivery covers the asked window.
   - e2e refetch, history, short-vendor, divergence, snapped-Gateway cases: **unchanged** —
     their windows are interior or their asserts derive from `CADENCE`.
4. **Live probe + docs sync + status** — `uv run pytest tests/parity` at whatever hour it is (the
   probe is the acceptance criterion precisely because it must no longer care); then:
   [ADR-0003 §cadence](../../adr/0003-provenance-and-origin.md) — the forward-edge bullet gains the
   window-quantum form and the two-clocks sentence; [#18](../../concerns.md#18-clock-anchored-footprint-fidelity)
   — "the numbers, not the shape" corrected, the probe record (both edges), residue restated
   (archive lower edge; real availability signal → `ideas.md`);
   [retentive-store ticket](../../tickets/done/01-0115-retentive-store-freshness.md) — the open-ended
   member agenda item (one-sided open + `ANY` designed together; the edge's omitted-`end` flip
   and the narration sentence decided there); [delivery status](../../tickets/README.md) — 0112 row
   → Done, current-stage note (the 003c landing's probe re-armed and passing);
   [edge/mcp.md](../../edge/mcp.md) needs **no contract change** (no absolute horizon is pinned
   there; the narration invariant's mechanism is untouched). Ticket criteria checked; ticket +
   this RFC → `done/`.

## Compatibility and rollout

- **No schema change; no new contract semantics.** The omitted-`end` response length becomes
  day-dependent (384 at 00:xx UTC down to 361 at 23:xx) — previously it was 384-and-failing; the
  description already tells callers `valid_time` is the disclosure.
- Narration changes "16 days" → "15 days" — conservative, user-accepted; becomes narration's own
  question again at the open-ended flip (retentive-store align).
- The parity check's compared window varies with run hour — reader-driven, no reader change.

## Scope limits and follow-ups

- **Archive lower edge (~92 d)** — the vendor serves it; we do not declare it. A product-scope
  decision (history through `forecast_hourly`: provenance/freshness semantics for past data,
  payload, parity evidence) recorded at [#18](../../concerns.md#18-clock-anchored-footprint-fidelity)
  as unlocked residue, not planned here.
- **Open-ended request member** ("no bounds — whatever is available") — reserved vocabulary
  (006's `ANY`, the "deferred m4 form"); designed at the retentive-store align together with the
  whole-axis form, where the edge's omitted-`end` flip and the divergence-as-default judgement
  are made with retention landing in the same ticket.
- **Real availability signal** from the vendor — stays `ideas.md` (#18's recorded end-state).
