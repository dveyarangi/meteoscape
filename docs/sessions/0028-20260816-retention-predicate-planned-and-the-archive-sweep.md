# 0028 · 2026-08-11 (evening) → 2026-08-16 · Retention planned as a predicate; the corpus swept back into shape

**Scope:** two stretches, recorded together because the first never got a record of its own. The
2026-08-11 evening and 08-12 work — the `shelf` rename in code, retention becoming an axis predicate
across the durable docs, TWC's live capture, ticket 0119 and both RFCs, one dream — landed after
session 0027 was already written at 14:16 that day. Then, on 08-16, a `/recall` that found no code
work in flight and five pieces of documentation drift, all repaired.

## Work done

**2026-08-11 evening → 08-12** *(reconstructed from the artifacts; each landed with its own record,
so nothing is restated here)*

- **`CadenceDef.window_quantum` → `shelf`** in code (`3394b60`) — the field names the vendor's
  serving calendar, not a property of the window. Landed ahead of its ticket so TWC would not ship
  on the old name; behaviour-neutral.
- **Retention became an axis predicate across the durable corpus** (`848dc93`, `6d1be99`) —
  ADR-0002, ADR-0003, architecture, glossary, the provider edge record, concerns, ideas. Both
  architecture Reservoir passages previously read "missing or stale" with no coverage clause at all:
  the containment test in the code had never been in the architecture.
- **TWC's live capture ran** against the operator's key, all seven durations at the pilot site — answering
  more than it was for, including the next-whole-hour series start that minted **0119**.
- **Ticket 0119 and RFCs for both 0119 and 0120 written**, ~1 300 lines, each validated twice.
- **A dream on provenance, reach, and nodata** (`da20f0e`).
- **The artifact-conventions slice** — `TICKET-FORMAT.md` minted, and numbering, status vocabulary,
  the ticket skeleton, and the queue shape lifted out of the delivery README and `/to-tickets` into
  it; `/align`, `/conclude`, `/plan-impl`, `/denoise` each given the conventions they own. Committed
  with this session, having sat uncommitted since.

**2026-08-16**

- **`/recall`** — the tree is green (308 deterministic tests) with no code work in flight; 0119 is
  planned to the stage level and entirely unimplemented (`satisfied_by` absent, `_required_coverage`
  still standing). Five pieces of drift found while reading.
- **The archive sweep, four months late in one respect.** `docs/sessions/historical/` renamed to
  `history/` — `/conclude`, `/denoise`, and the directory README all said `history/` and the
  filesystem was the lone dissenter. Sessions 0020–0025 (08-04 … 08-08) moved to `history/2026-08/`,
  their relative links re-depthed to match the convention the 2026-07 archive had already set.
- **A link sweep over the whole corpus** — 2 277 relative links under `docs/` and `.agents/`, all
  resolving. One session-to-session link removed from 0025, against `/denoise`'s rule.
- **Delivery-status `Last updated`** corrected to 2026-08-11, and what that field means written down.
- **`.idea/` gitignored.**

## Settled this session

- **`Last updated` on the delivery status tracks delivery state, not the edit date** — a link repair
  does not advance it; a status flip or a minted ticket does →
  [TICKET-FORMAT.md § The queue](../../.agents/skills/to-tickets/TICKET-FORMAT.md#the-queue).
- **The session archive is `docs/sessions/history/YYYY-MM/`** — three documents against one
  directory name, and the documents won → [/conclude](../../.agents/skills/conclude/SKILL.md).
- **A convention may be owned by the skill that maintains its artifact, not only by a central
  registry** — the assumption the conventions sweep started from, amended where the RFC-naming
  decision broke it → [0200](../tickets/01-0200-artifact-conventions-sweep.md) scope item 2.
- **The 08-11 evening stretch gets no reconstructed session of its own** — its decisions all live in
  ADR-0002/0003, the glossary, and the two RFCs, and inventing a record of someone else's reasoning
  would put guesses into a corpus that is by rule never rewritten. This record covers it instead.

## Found, not settled — new pressure

- **[Documentation link integrity is ungated](../cicd.md#ci-pipeline).** The corpus is deliberately
  cross-referential, so a link that stops resolving is a structural loss, not a cosmetic one — and
  every archive move or `done/` close re-depths links silently. The check is a manual sweep at
  landing time, which means it is skipped exactly when a session runs long. Session 0025 named this
  in prose after breaking twenty links; it had no owner until now. Not yet ticketed.
- **The TWC capture exists on one machine.** It sits under gitignored `tmp/`, and every declaration
  in the TWC plan rests on it. Losing it costs a re-run against the metered key →
  [RFC 0120 stage 0](../rfc/01-0120-twc-provider.md).

## Open questions

All live in their owning documents; cited here, not restated.

- The predicate's per-parameter clock re-read, and diverging reaches →
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback).
- Whether anything here narrows [#21](../concerns.md#21-serves-extent-vs-project-crop-ability) —
  the family is the same, the off-phase case is untouched.
- Tick convention → [#48](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick)
  / [0126](../tickets/01-0126-tick-convention-declaration.md), still waiting on TWC as the second
  convention.
- Parity enforcement and routing → [#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).
- The full artifact roster analysis → [0200](../tickets/01-0200-artifact-conventions-sweep.md),
  whose align has not run; today's slice is a down payment, not the ticket.

## Continuation

1. **0119 stage 1** — the predicate pair in `manifold/`, red → green, before the Reservoir is
   touched. Six axis-level tests, one per case, each encoding a different reason.
2. **Land the TWC fixture** out of `tmp/` before 0120 stage 1, not alongside it.
3. **0119 → 011 → 004 → 010 → 008** unchanged; 0126 after TWC.

## Advisory read

**What is great.** The two RFCs written on 08-11 are the strongest planning artifacts this project
has produced. RFC 0119's four-case table does something rare: it argues *against* the obvious repair
(overlap) by finding the single case that breaks it, and then says in the test plan that this case is
"the one most likely to be 'fixed' into overlap later" and carries its reason in the test. That is a
plan defending itself against its own future reader.

**What is good enough.** Today's drift repair. Five items, four mechanical, one escalated to you
because it wasn't. Nothing needed an align, which is the correct outcome for a maintenance pass — if
routine cleanup keeps surfacing design decisions, the cleanup is misnamed.

**What is questionable.** *The `/denoise` cadence, again.* Session 0027's advisory read asked for a
`/denoise` pass "on a cadence rather than on demand," and then five days passed in which six sessions
aged out of the window, a directory name diverged from three documents describing it, and a
session-to-session link survived a rule that has forbidden it for weeks. The recommendation was
correct and was not acted on. It will keep being correct.

**What is missing.** Still a running TWC leaf. Session 0027 said "what is missing: a real payload";
the payload arrived that evening and is sitting in `tmp/`. Five days later there is more plan and no
more code. The gap between 0119 being *fully planned* and *entirely unwritten* is now the single
largest thing in the project.

**What is out of balance.** The same ratio 0027 flagged, and it did not correct: since 007 closed,
this project has produced roughly 2 000 lines of documentation movement and 18 lines of `src` change.
0027 called that "right for an align-heavy stretch and alarming if it repeated through
implementation." It has now repeated through a stretch that contained no implementation at all. The
plans are excellent; the tree has not moved since 08-11.

**Hidden edges.** Two, both about single points of failure that read as ordinary. The TWC capture in
`tmp/` — now written down, previously known only to whoever ran it. And the fact that this project's
strongest defect-finding instrument is *reading documents against each other*, which quietly assumes
the links between them resolve; nothing checks that, and the assumption is invisible until an archive
move breaks it.

**What would make life easier.** A CI link check — the concrete form of the `/denoise` cadence
request, and the one piece of this that a machine can hold better than a discipline can.

**What next.** 0119 stage 1. The planning is done; it has been done for five days.
