# 0022 · 2026-08-06 · 003c reviewed and landed; 0112 planned; ticket-altitude rule

**Scope:** code review of the Cursor-authored 003c implementation; the live parity probe's 400
root-caused to a **shape** error in the availability declaration; the day-anchored fix planned
(ticket 0112, RFC 0010); the ticket-criteria altitude rule extracted from a review sidebar into
the skills.

## Work done

- **Reviewed the 003c landing** against [RFC 0008](../rfc/done/0008-20260725-003c-request-shaping.md):
  faithful throughout — edge holds no tick arithmetic, pinned names/messages/fixtures match, the
  [MCP edge record](../edge/mcp.md) update is thorough, gate green (225 deterministic tests, ruff,
  format, pyright). Two defensible deviations recorded in review only (`_t_extent` subsuming the
  RFC's `_t_upper` sketch, which would not have typechecked; `_horizon_sentence` merging two
  pinned helpers).
- **The acceptance probe failed live** — `runtime-failure: upstream HTTP 400` on the 384-tick
  default. Probed the vendor: availability is **day-quantized forward**
  (`end_hour = today00+16d−1h` → 200, `today00+16d` → 400) and **archive-deep backward**
  (~92 days serve through the same endpoint), while our `CadenceDef.valid_time` slides with the
  clock — so the default 400s for ~23 h of every day and the landing's probe had passed only by
  running near UTC midnight. [#18](../concerns.md#18-clock-anchored-footprint-fidelity)'s "the
  numbers, not the shape" clause is falsified for this vendor.
- **Discussed and rejected two fixes**: cutting `max_lead` to 15 d (hides a shape error by cutting
  a day of real offering) and a Probe/leaf-side clamp (the crop already exists — `clip` against
  the declaration; a vendor-face clamp leaves the declaration lying to admission, narration, and
  006's store, and defeats the parity guard that caught this). The **open-ended request member**
  ("no bounds — whatever is available") was recognized as 006's reserved `ANY` vocabulary and
  routed to the retentive-store align rather than minted alone.
- **Planned the fix**: ticket
  [0112 — day-anchored availability window](../tickets/done/01-0112-day-anchored-availability-window.md)
  (Ready, queue position between 003c and the retentive store) and
  [RFC 0010](../rfc/done/0010-20260806-day-anchored-availability-window.md) — `CadenceDef.window_quantum`,
  Open-Meteo declaring its probed truth, narration flooring to whole days, provenance/freshness
  provably untouched.
- **Extracted the altitude rule into the skills** (align): 0112's first-draft criteria carried
  code shape, which prompted the rule — criteria state observable behavior; shape is the RFC's;
  refactor criteria are behavior-preserved + machine-enforced constraint + dependents unblocked;
  no ticketless RFCs. The user then reworked `to-tickets` from PRD-only into a parent-generic
  decomposition skill (PRD / coarse ticket / discussed chunk) with the rule embedded.

## Settled this session

- **Open-Meteo's availability shape, live-probed** (day-quantized forward edge, archive-deep
  lower) and the day-anchored declaration as its fix →
  [0112 ticket](../tickets/done/01-0112-day-anchored-availability-window.md) (why),
  [RFC 0010](../rfc/done/0010-20260806-day-anchored-availability-window.md) (how).
- **No declaration cut, no vendor-face clamp** — the declaration layer owns vendor truth; the
  parity guard must stay able to catch mis-declarations → 0112 ticket §Why.
- **The open-ended request member is designed at the retentive-store align, together with `ANY`**
  (the edge's omitted-`end` flip and narration-as-floor decided there) → RFC 0010 stage 4 routes
  it onto [01-0115](../tickets/done/01-0115-retentive-store-freshness.md) at 0112's landing.
- **Ticket criteria hold the behavior altitude; an RFC always implements a ticket** →
  [`to-tickets` skill](../../.agents/skills/to-tickets/SKILL.md) (the rule),
  [`plan-impl` skill](../../.agents/skills/plan-impl/SKILL.md) (no ticketless RFCs).
- **The delivery status honestly records the probe finding** (no more "served 384 live" claim) →
  [delivery status](../tickets/README.md) current-stage.

## Open questions

All owned elsewhere; none live only here:

- **The delivery-status "tickets own implementation detail" phrasing** contradicts the altitude
  rule → carried on the
  [artifact-conventions sweep](../tickets/01-0200-artifact-conventions-sweep.md)'s findings list.
- **Archive lower edge (~92 d) and the real availability signal** →
  [#18](../concerns.md#18-clock-anchored-footprint-fidelity) residue (restated at 0112's
  landing per RFC 0010 stage 4).
- **Refill scope, partial-warm verification, #42 narrowing, open-ended member** — the
  retentive-store align's agenda →
  [01-0115](../tickets/done/01-0115-retentive-store-freshness.md), RFC 0010 stage 4.

## Continuation

- **Implement 0112 from RFC 0010** (four stages; the live parity run at an arbitrary hour is the
  acceptance). Its stage 4 carries the doc landing: ADR-0003 two-clocks amendment, #18
  correction, the 0115 agenda item, status flip.
- The 003c code and this session's planning/skill artifacts are committed in two commits
  (CODE: the 003c landing; DOCS: the review outcome, 0112/RFC 0010, skills); the untracked
  `.agents/skills/wayfinder/` remains deliberately uncommitted.
