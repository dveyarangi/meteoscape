# 0018 · 2026-07-25 · m3 lands; 003c planning pivots window fitting to the Snapped mode

One session, two arcs. **Arc 1:** [m3](../tickets/done/01-0080-provider-parity-checks.md) went
align → [RFC 0007](../rfc/done/0007-20260725-m3-provider-parity-checks.md) → Cursor
implementation → validation → landed, in a day — including a live acceptance run against real
Open-Meteo (1 passed, no retry consumed). **Arc 2:** 003c planning
([RFC 0008](../rfc/0008-20260725-003c-request-shaping.md)) survived three adversarial review
rounds, and the accumulated findings drove the window-fitting design off the edge and into the
algebra's reserved **Snapped mode** — minting
[m4](../tickets/01-0100-snapped-t-request-mode.md), which now precedes 003c. Decisions live in the
tickets, RFCs, and amended docs; this record carries the reasoning trail.

## Arc 1 — m3 (parity) in brief

- Aligned in five decisions (structural test split `tests/deterministic` / `tests/parity`,
  data-coupled harness at the MCP payload, direct-JSON reference reader, comparison spec, two-channel
  evidence); planned to one implementation; implemented faithfully by Cursor in five stages.
- The align's one engine find: `wind_from_uv` emitted an arbitrary 180.0° at `u = v = 0` — fixed as
  the **calm floor** (`CALM_SPEED_FLOOR`, epsilon guard, deliberately not a WMO calm policy), with
  the parity spec importing the same constant.
- Validation was clean; the two RFC underspecifications Cursor hit (`present is None` mask,
  `format_summary` secrets kwarg) were resolved *and back-synced into the RFC* — the doc-gap loop
  working as intended. Post-landing review contributed the fresh-root-per-retry rule (guards
  against 006's future retention pinning a stale run during the run-boundary retry).

## Arc 2 — how 003c planning became the Snapped pivot

The instructive part of the day. The sequence:

1. RFC 0008 planned the ticket's recorded semantics (containment admission; out-of-envelope →
   `capability-mismatch`). Review round 1 found four edge holes; fixed.
2. The user asked for relaxed semantics — "clamp to available data, no tricks" — and clamping was
   aligned, specified, and reviewed. Round 2 found a staging bug and a benign clock race; round 3
   found a *spurious-mismatch* race on the clamped lower edge, an empty-menu crash, and more.
3. The pattern behind every finding: the edge was **simulating at the wrong layer** what
   [ADR-0002](../adr/0002-data-model.md) already reserves as the Snapped mode ("step fixed,
   anchor/extent open, resolvable against a declared grid"). Moving fitting to resolution — the
   authority with one clock read — dissolves the clamp math, the races, the edge reach-fold, and
   most of the vendor-clamp failure class. The lesson worth keeping: **repeated review findings
   clustered in one code region are design pressure, not test debt.**
4. m4 was minted to own the mode (maintenance, before 003c), deliberately as a **tentative
   sketch** awaiting its own align. 003c was re-based and **denoised to final rules** — the
   containment → clamp → snapped trail is preserved at its owners (m4's Why; RFC 0008's hold
   banner), not in the ticket's body.

Decisions that *survived* the pivot and stand in 003c: **datetimes only** (loud bare-date
rejection reverses session 0013's day-cell rule while honoring its no-silently-short-answer
rationale), the empty-`parameters` rules, relative-horizon narration, and the
`Settings.default_horizon` deletion (v1-requirements already said "no configured default horizon" —
the code was behind the contract). Also verified: the ticket's `validate_calculators` criterion
was already satisfied by `weave`'s first step — annotated, no double call added.

Design clarifications banked into m4 during the questioning (so its align inherits arguments, not
open questions): no store dependency / no temporary bend (the resolver's own grid is the snap
target; ADR-0006's "domain lives only on the Coverage" is the request shape's natural partner);
mode-scoped assembly strictness (enumerable keeps the length assertion — it remains 006's refill
language; snapped validates response coherence); one generic axis member with T-only enablement
(X/Y is blocked by the Timeline-only invariant, not by machinery — with a falsifiable
wiring-not-algebra guard criterion); and [#23](../concerns.md#23-spatial-vs-temporal-regularaxis-types)'s
axis-type split assigned as m4's stage 0 on its own recorded trigger.

## Continuation

- **[/align m4](../tickets/01-0100-snapped-t-request-mode.md)** is the next design session: firm the
  axis member's shape, the intersective `matches` wording, the resolution home, and write the
  ADR-0002/ADR-0004 amendments. Then re-stage RFC 0008 and implement m4 → 003c.
- **Push pending:** two commits ahead of origin at session end.
- From the day's project-level advisory, still unowned: **resolution logging** (Phase-1 requirement,
  no ticket), **#39 embedding surface** (release criteria 10–11 have no ticket), **second-provider
  key verification** (TWC access is unverified; any keyed provider satisfies the secrets seam), and
  the **README adoption block** (MCP client config + sample provenance response — servable today).
- m3 follow-ons stay recorded in its done ticket (retry TODO, scheduled parity automation).

## Process notes

- The m3 cycle validated the full loop at one-ticket-per-day cadence: parallel-RFC align,
  unambiguous plan, external implementation, doc-gap validation lens, stage-6 sync.
- Adversarial review passes ("what is underspecified / contradictory / hidden edges?") repeatedly
  paid for themselves — including catching defects in freshly written plan text (the RFC's own
  snippet bugs) and, cumulatively, forcing the architecture-level correction.
- Supersession hygiene: while a pivot is in motion, strike-and-annotate in place; once settled,
  **denoise the ticket to final rules** and leave the archaeology at the decision's owner. The
  triple-layered 003c was unreadable until that pass.
- When amending a contract doc mid-pivot, reference the *contract owner* (ADR), not the in-flight
  ticket — caught by the denoise layering rule in v1-requirements.
