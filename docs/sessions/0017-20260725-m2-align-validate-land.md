# 0017 · 2026-07-24/25 · m2 align, validation, and landing

An align-then-validate cycle over [m2](../tickets/done/m2-dissolve-node-countable.md): ticket
reviewed against the architecture docs for "invisible edges," [RFC 0006](../rfc/done/0006-20260724-m2-dissolve-node-countable.md)
built in parallel with the grilling, implementation done externally (Cursor), then validated here
with a doc-vs-code lens. Landed as three commits (CODE m2, DOCS m2, DOCS agents). Rules live in the
ticket, the RFC, and the amended ADRs; this record carries the reasoning trail.

## What the align found (and how it resolved)

- **The provider-exact lattice channel dies with m2 — and that is fine, for a reason worth keeping.**
  The worry: deleting `Countable.domain` removes the only way a provider could hand its exact grid to
  the `StoreFactory`. Dissolved by two facts: a non-materialized provider's reach is *continuous*
  (`FootprintCapability` — no grid to read), and the only enumerable-reach providers are materialized
  and get no store at all — so a capability can never feed the factory, and the catalogue's
  `OfferingSpec.store` (authored beside the manifest by whoever knows the vendor grid) was already
  the real declaration channel. The enumerable-but-unholdable residual (cloud ARCO) stays with
  [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
- **The binder invariant became loud in both directions** — a configured store on a materialized
  offering was being *silently discarded*; now both contradictions raise `CompositionError`.
- **Doc updates became ticket rows.** The ticket originally scheduled no doc work despite reversing
  a recorded ADR-0006 clause; a "Docs to sync" section now travels with the ticket.
- **Source-definition docs deliberately untouched.** "A Source is `Reservoir(store, Provider)`"
  stays true for every v1 source; the widening (a bare-Provider Source role) is recorded at #37's
  trigger, not applied speculatively.

## Validation pass (the Cursor → Claude seam)

The implementation was faithful — every ticket row as specified, gates green. One real finding, and
its cause was a **doc gap, not a code mistake**: acceptance criterion 3's "serves through the
Arbiter" half was silently weakened to a capability-composition assert, because the base
`FakeProvider.project` raises by design and neither ticket nor RFC named a fixture that could
project. Lesson for the next RFC: when a RED test needs a capability the existing fixtures lack, the
RFC must say which fixture provides it. Fixed with a projecting fake and an end-to-end storeless
serve test (on-grid per #37).

The sync-arch pass then found **six stale doc sites beyond the ticket's own list** — including a
mermaid flowchart in ADR-0005 still branching on "provider declares a native lattice?" — all
recorded in the ticket's Docs-to-sync section and synced. Diagram nodes are grep-resistant; worth
checking explicitly in future syncs.

## Simplify pass

Four parallel review agents; five findings applied on approval: resolve-the-store-knob-once in the
binder, a named `_is_materialized` predicate, `wire_source` as the single home of the source-wiring
rule (production and `test_arbiter._producers` both call it — the mirror-drift class m2 itself was
killing), and shared `RecordingProvider` / `coverage_record` fixtures replacing per-file copies.
`ruff format --check` also surfaced a long-line reflow the other gates never see — it was not part
of the habitual gate set.

## Continuation

- **[m3 — Provider parity checks](../tickets/m3-provider-parity-checks.md)** is Ready and next in
  the maintenance stream; must land before 004's second Provider.
- **003c** (request shaping) and **006** (retentive store) both unblocked; 006's assumed
  storeless/private-lattice shape is now in place.
- **Nothing pushed** — the local commit backlog (through the three commits of this session) awaits
  an explicit push decision.
- Consider adding `ruff format --check` to the standing gate set (commit skill / CI) — it caught a
  drift the lint gate misses.

## Process notes

- The parallel-RFC pattern worked: initialize the RFC at the first resolved question, append
  decisions and code shapes as they land, and the implementation session starts with zero ambiguity.
- Review-type skills should **report first, apply on approval** in this project — the simplify pass
  initially applied its fixes and was rolled back before being re-applied on request.
- The validation lens "name the doc gap behind each code finding" produced exactly one finding and
  it was actionable on both sides (test added, RFC rule for next time).
