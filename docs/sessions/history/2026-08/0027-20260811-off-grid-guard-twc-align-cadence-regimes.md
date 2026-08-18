# 0027 · 2026-08-11 · 007 closes as a guard, TWC aligned, and the cadence model splits in two

**Scope:** [007](../../../tickets/done/01-0117-off-grid-homogenization.md) turned out to be already
*behaving* and never *guarded*, so it landed as a guard ticket with no `src` logic. Its align renamed
the read-time vocabulary corpus-wide. Planning [011](../../../tickets/done/01-0120-twc-provider.md) against real
vendor documentation then produced three findings the code could not have surfaced — a live
precipitation defect, a two-regime split in the cadence model, and a units choice that turned on a
data type. Closed with `/denoise` and this record.

## Work done

- **007 recalled, aligned, planned, implemented, reviewed, committed.** The recall found the ticket's
  headline behaviour already true in the tree; the align established why; [RFC
  0016](../../../rfc/done/0016-20260810-off-grid-homogenization.md) planned it as tests-and-records. Cursor
  implemented; review found four defects (two CI-blocking) and all three **mutation checks** behaved
  as predicted, with the tree restored byte-identical. Committed `ae74619` (code) / `19679fa` (docs).
- **Swept `kernel` → `Resampler`** across the source-of-truth corpus — twelve sites in ADR-0001/2/3/4/6,
  architecture, concerns, parameters, and product-roadmap. The *Calculator* kernel sense was left
  alone; it is why the resampling sense was reserved against in the first place.
- **Sourced TWC's API from the vendor's own documentation** (portfolio + enterprise hourly endpoint,
  both Google Docs behind `twcapi.co` shortlinks; cited in the leaf's module docstring per the align).
  The repo previously held no TWC specifics at all.
- **[RFC 0017](../../../rfc/done/01-0120-twc-provider.md) written and reviewed twice**, each pass finding
  real defects in the previous one — including two of my own mis-stated mechanisms.
- **`/denoise` pass** (user-run, in parallel) plus RFC 0016 filed to `rfc/done/`.

## Settled this session

- **Enclosing, not nearest** — one enclosing cell exists, and *nearest* is a question only with several
  candidates, which point-shaped records over a sparse store never produce →
  [v1-requirements §4](../../../v1-requirements.md), already fixed by ADR-0006.
- **The read-time rule is a *Resampler*, and v1's is identity** — `kernel` was reserved because the
  Calculator sense owns it → [glossary](../../../glossary.md).
- **007 builds nothing; the claim/transfer split already existed** — `_relabel_onto` is the claim,
  `sampling.resample` the transfer → [RFC 0016](../../../rfc/done/0016-20260810-off-grid-homogenization.md).
- **Point-exactness lives on the Coverage contract, not the MCP wire** — `serialize_coverage` emits no
  coordinate, so that surface promises the observable consequence instead →
  [edge/mcp.md](../../../edge/mcp.md).
- **[#21](../../../concerns.md#21-serves-extent-vs-project-crop-ability) is not closed by 007** — it named
  "registry at 007", which 007 does not deliver; trigger repointed.
- **TWC: duration is offering *identity*, cadence is offering *policy*** — name against a catalogue row
  (boot-checked), settings for the knob → [ticket 011](../../../tickets/done/01-0120-twc-provider.md).
- **`units=m`, not `units=s`** — the two differ only in the wind unit, and `windSpeed` is an *Integer*,
  so SI's "no conversion" was bought with 3.6× coarser wind → RFC 0017.
- **Two cadence regimes — run, and fetch bucket** — a provider publishing no run schedule carries
  `L = 0` and `A = floor(fetched_at, Δ)`, a bucket rather than a run; the regime is per-provider and a
  deployment runs both → [ADR-0003 § Two regimes](../../../adr/0003-provenance-and-origin.md), *Fetch
  bucket* minted in the [glossary](../../../glossary.md).
- **Anchored expiry kept, its cost accepted** — no real event at the grid line means TTL averages Δ/2
  and the deployment spends ~2× the configured interval →
  [#18](../../../concerns.md#18-clock-anchored-footprint-fidelity).
- **Parity stays manual for TWC** — prepared in the ticket, run once by hand, scheduling deferred →
  [#41](../../../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).
- **Wider TWC licence is roadmap work in four differently-shaped steps** →
  [product-roadmap Phase 2](../../../product-roadmap.md).

## Found, not settled — new pressure

- **[#48 — a tap cannot declare where its value sits relative to the tick](../../../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick).**
  Open-Meteo's `precipitation` is the *preceding* hour while the lattice declares the *following* one,
  so every value is labelled an hour late; TWC's `qpf` matches. Widened once more when TWC's response
  turned out to mix three temporal semantics in one payload. Repaired at
  [0126](../../../tickets/01-0126-tick-convention-declaration.md), which waits for TWC deliberately — the
  second convention is what stops the fix encoding the first as the default.
- **What parity structurally cannot verify** — semantics and declared Z heights, because the reference
  reader reads the same API under the same assumptions → [edge/provider.md](../../../edge/provider.md).

## Open questions

All live in their owning documents; cited here, not restated.

- Tick convention and cell statistic → [#48](../../../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick) / [0126](../../../tickets/01-0126-tick-convention-declaration.md).
- Whether the Δ/2 spend trade survives measurement → [#18](../../../concerns.md#18-clock-anchored-footprint-fidelity), for the [ledger](../../../tickets/02-0124-vendor-call-ledger.md)'s align.
- Whether the run archive declines runless producers or records the distinction → [02-0134](../../../tickets/02-0134-forecast-run-archive-source.md).
- TWC's live unknowns — licensed duration, delivered tick count per offering, whether 12 h is right,
  and where the series starts → RFC 0017 stage 5.

## Continuation

1. **RFC 0017 stage 0 needs the operator's key** — one live call, scrubbed, becomes the test fixture.
   The envelope's nesting is the one vendor fact the documentation does not pin, so nothing downstream
   should be written against a guess.
2. **011 → 004 → 010 → 008**, unchanged; 0126 slots in after TWC.
3. This record and the session's documentation are committed; **ticket 011 and RFC 0017 are held back**
   at the operator's instruction, being work in flight.

## Advisory read

**What is great.** The documentation is load-bearing in a way most projects only claim: three separate
defects this session were found *by reading it against itself* — "nearest enclosing" naming no cell,
"registry at 007" pointing at a ticket that delivers no registry, and a precipitation window
contradicting the lattice. None were findable by running anything.

**What is good enough.** The guard-ticket outcome. 007 delivering no logic reads like an
anticlimax and is the correct result: it converted an assumed feature into a verified one, and the
mutation checks proved the tests would notice if it broke.

**What is questionable.** *My own prose discipline.* Two of the three findings in the final review were
mine, introduced by the very pass removing that defect class — an unguarded invariant, and a ticket
line contradicting its own paragraph three lines up. The failure mode is consistent: when terminology
changes, I fix the sentence in front of me and leave its neighbours. The align skill's end-of-session
consistency sweep exists for this, and it was skipped twice.

**What is missing.** A real payload. Every TWC declaration rests on vendor prose; the envelope's shape,
the tick count, and the refresh cadence are all unverified. Stage 0 is the smallest thing that changes
this and it is blocked on a key.

**What is out of balance.** Documentation volume against code volume. This session produced one
`src` docstring change and roughly 1,300 lines of documentation movement. That ratio is right for an
align-heavy stretch and would be alarming if it repeated through implementation.

**Hidden edges.** Two. `expiration` anchoring silently doubles vendor spend for a runless provider —
the ledger will surface this as an anomaly unless its align is told to expect it. And a *fetch bucket*
filed under a run key would archive fiction, which nobody would notice for a year; flagged in 02-0134.

**What would make life easier.** A `/denoise` pass on a cadence rather than on demand. The recurring
defect class is prose drift, not code coupling — every review this session confirmed it.

**What next.** Stage 0, then 011's implementation.
