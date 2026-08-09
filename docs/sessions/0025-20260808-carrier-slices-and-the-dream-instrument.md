# Session 0025 · 2026-08-08 (running past midnight) · Two store slices, one capability form, and a new instrument

The long day after the release-02 restructure. [Session 0024](./0024-20260808-purpose-release-02-twc-revert.md)
closed at 04:23; work resumed at 13:50 and ran through the small hours of the 9th. Three tickets
landed, one maintenance refactor cleared the ground beneath them, three skills changed, and one new
skill was written and immediately earned its keep.

**The arc.**

- **13:50 — slice 1 lands.** [`ANY` as the boundless snapped member](../tickets/done/01-0115.0010-any-boundless-member.md)
  (RFC 0011): the vocabulary only — boundless member, `ground`'s open arm, shared `clip` tolerance.
  No behaviour change, by design.
- **13:56 and 15:07 — [RFC 0012](../rfc/done/0012-20260808-multidomain-carrier-timeline.md) hardened twice
  before a line of its code was written.** The first pass found the pre-fetch window justification was
  simply wrong — an open T is exempt from the fold's agreement law, so the single fetch window is
  guaranteed by the shape's one `CadenceDef`, not by the fold. The second pass read `_as_delivered` and
  `_cropped` as they actually stood and collapsed three genuinely two-way choices to one apiece: where
  the fold lives, who owns fault classification, and how the provenance plane is built.
- **19:03 — [0113](../tickets/done/01-0113-per-parameter-materialized-capability.md).**
  `FootprintCapability` becomes `GranularCapability`. The class had been *named and documented for one
  of its two uses*, which is exactly why both the multi-domain carrier and the retentive store had been
  deferring to "a form yet to be minted" that already existed. Nothing behavioural moved.
  [#46](../concerns.md#46-composition-failure-attribution-is-paid-inside-geometry) was minted for the
  half deliberately deferred.
- **21:45 — two map gaps closed.** `require_separable` reached
  [module-layout](../module-layout.md); [architecture.md](../architecture.md)'s concern index had
  drifted seven entries behind and now resolves all of them.
- **21:52 — composition folds and their errors move to the composing nodes.** `capability.py` becomes
  pure value types; the duplicated separability guard collapses into one `require_separable` that
  authors the shared sentence while each caller supplies its own rule and declarer. One of #46's three
  symptoms resolved, the concern rescoped to the other two.
- **21:52 — [`/implement`](../../.agents/skills/implement/SKILL.md) hands off to `/review-impl` before
  `/sync-arch`**, because the two passes check opposite directions.
- **Past midnight — [slice 2 implemented](../tickets/done/01-0115.0020-multidomain-carrier-timeline.md).**
  `clip` widened to optional bounds across five axis kinds, `ground`'s boundless arm dissolved into it,
  `open_axes` minted, `agreed_geometry` given the request-derived licence while keeping its single
  return, `CoverageSet` minted beside `CoverageRecord`, `TimelineProvider.project` reduced to one branch
  on boundlessness with both eager folds retired. 261 tests green, `pyright` clean.
- **The [`dream`](../../.agents/skills/dream/SKILL.md) skill was written and used twice** — the first
  dream was discarded, the second kept
  ([вывеска, меню и расписка](../dreams/20260809-vyveska-menyu-i-raspiska.md)) — and
  [`/improve-comments`](../../.agents/skills/improve-comments/SKILL.md) gained a `TODO (temporary)`
  convention, applied to its two live instances (`Shortfall`'s raise, `StubStore`).
  [`/conclude`](../../.agents/skills/conclude/SKILL.md) was widened to a day spanning chats and
  external changes, plus the `/advise` questions — this record is its first output.
- **Finally `/recall` → `/review-impl` over slice 2.** The review's first instinct was to tidy an
  out-of-taxonomy error by casting it into `CapabilityMismatch`. The **discarded first dream** — a
  library where two very different refusals print the same blank slip, one meaning *"we do not have
  it"* and one *"it is written in a script none of us reads"* — sent the review to
  [#21](../concerns.md#21-serves-extent-vs-project-crop-ability) and
  [#36](../concerns.md#36-unserved-and-uncomparable-are-indistinguishable), which had settled it in
  the opposite direction weeks earlier. **The instrument built at the end of the day corrected a wrong
  conclusion within hours of existing**, with no authority of its own — purely by pointing at documents
  that were already right. The dream itself was not kept, which costs nothing: what it produced lives
  in the edge record, and a dream owns no fact by design.

## Settled (one line each; the reference is the durable home)

- **`ANY` is the boundless snapped member** (`interval=None`), so `SelectableAxis` gains no new kind →
  [ADR-0002](../adr/0002-data-model.md), [edge/provider.md](../edge/provider.md).
- **`GranularCapability` is the per-parameter own-geometry form**, one row for both uses; "materialized
  ⇒ enumerable reach" scopes to the co-domained form where the type states it →
  [ADR-0007](../adr/0007-capability-carries-its-domain.md), [ADR-0004](../adr/0004-producer-resolution-and-capability.md).
- **Each composition rule is the sole author of its own error**, and a Calculator's fold belongs to its
  node — capability forms carry composed results and nothing else →
  [ADR-0007](../adr/0007-capability-carries-its-domain.md).
- **Per-parameter granularity is not ADR-0006's unit granularity** — the shared word, disambiguated →
  [ADR-0004](../adr/0004-producer-resolution-and-capability.md).
- **The multi-domain carrier and its names**: `agreed_geometry` (singular, request-derived licence) and
  `CoverageSet` — the edge record's naming checkpoint is closed →
  [edge/provider.md](../edge/provider.md#resolution--how-a-request-becomes-an-answer-geometry),
  [glossary](../glossary.md).
- **Taking an axis whole is `clip` with no bounds, not a second operation** — a clock-relative axis
  reads its clock exactly once inside the call → [ADR-0002](../adr/0002-data-model.md),
  [glossary §Clip](../glossary.md).
- **The answer discipline on the parameter facet**: wider than the ask is permitted, narrower never;
  what it may carry is the producer's natural fetch unit →
  [ADR-0001](../adr/0001-manifold-algebra-and-composition.md).
- **The engine's assert is a fourth outcome, deliberately outside the leaf taxonomy** — never caught,
  never re-categorised, never pinned by a test as expected refusal →
  [edge/provider.md §Outcomes](../edge/provider.md#outcomes), owned by #21 / #36.
- **Pinned Z and vantage Z are different promises**, and a vantage relabel is an ∃-claim never a
  ∀-claim — same rule as [#25](../concerns.md#25-root-store-unit-reuse-across-vantage-windows), second
  site → [edge/provider.md §Response](../edge/provider.md#response--what-a-leaf-returns).
- **The natural fetch unit is unwitnessed, not deferred** — a wrapper constant binding every timeline
  vendor; 011 is the witness → [edge/provider.md §Request](../edge/provider.md#request--what-a-leaf-may-be-handed),
  [#43](../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence).
- **Two code silences named as deliberate** rather than left to look like health — the retired
  empty-records guard ([timeline.py](../../src/meteoscape/nodes/providers/timeline.py)) and `open_axes`'
  empty answer for any non-`SelectionDomain` request ([domain.py](../../src/meteoscape/manifold/domain.py)),
  which [#42](../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method)'s winner
  must be added to first.
- **Temporary code is marked at the site** → [`/improve-comments`](../../.agents/skills/improve-comments/SKILL.md).
- **Dreams own no fact and are not maintained against the code** → [docs/README.md](../README.md).
- **`/implement` runs `/review-impl` before `/sync-arch`**; **`/conclude` covers a day, not a chat** →
  the respective skills.

## Delivery state

Three tickets Done this day: [0115.0010](../tickets/done/01-0115.0010-any-boundless-member.md),
[0113](../tickets/done/01-0113-per-parameter-materialized-capability.md), and
[0115.0020](../tickets/done/01-0115.0020-multidomain-carrier-timeline.md) — the last one closed at the
end of the session, with [RFC 0012](../rfc/done/0012-20260808-multidomain-carrier-timeline.md) moved to
`rfc/done` and the delivery map updated. `/sync-arch` finished: the carrier now has its
architecture-level home. Slices 3–4 (RFCs 0013/0014) unstarted.
Queue: [delivery README](../tickets/README.md).

## Open questions (all owned elsewhere; none live only here)

- Composition-failure attribution: producer identity and operator prose inside `manifold/domain.py`,
  and `UnionCapability`'s unread `ProducerKey` keying — two of three symptoms remain, waiting on a real
  failing profile rather than taste →
  [#46](../concerns.md#46-composition-failure-attribution-is-paid-inside-geometry).
- Whether the timeline shape's fetch unit is algebra or one vendor's scoop →
  [#43](../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence) at 011.
- Closing the admit-then-cannot-crop gap inside `serves` → [#21](../concerns.md#21-serves-extent-vs-project-crop-ability);
  the reason code that would make the two refusals distinguishable to an operator →
  [#36](../concerns.md#36-unserved-and-uncomparable-are-indistinguishable), [#14](../concerns.md#14-resolution-trace-and-observability).
- Reuse of an ∃-labelled vantage unit for a narrower window → [#25](../concerns.md#25-root-store-unit-reuse-across-vantage-windows).

**Deliberately *not* filed**, so no later reader hunts for a home: `CoverageSet.project`'s
empty-parameter precondition is docstring-stated and unchecked — the posture
[#31](../concerns.md#31-positional-alignment-is-asserted-never-checked) already defends; and
`agreed_geometry`'s accumulation of `members` it reads only at `[0]` is a vestige of the rejected group
return, a cleanup rather than a question.

## Advisory read

**What is great.** The documents held, twice, in the same day. 0113 discovered that a form both pending
slices were waiting on already existed under a name describing one of its two uses. The slice-2 review
had a plausible, tidy-looking fix stopped by two concerns written weeks earlier — before code, by
reading. That is the return on this project's documentation investment, collected in one day.

**One theme runs through everything today**, and it is worth naming because it recurred four times
independently: *refuse to let one name carry two facts.* A capability form named for one of its two
uses. A generic layer raising errors another layer had to translate. A category cast that would have
merged "I do not have it" with "I cannot read it". A blank slip meaning two opposite things. Every
significant move today was a de-conflation.

**What is good enough.** RFC 0012's implementation fidelity — seven decisions, five stages, each
acceptance criterion pinned. Three deviations went unremarked (a third guard retired, the assert's
category, the fixture's real blast radius), but all three were findable *from the docs*, which is the
property that matters.

**What is questionable.** Two passes of RFC hardening before implementation is a real cost, and it was
right both times — but it also means the RFC is now doing work an ADR or the edge record should carry
permanently. Watch that RFCs stop being the place hard thinking lives, since they archive.

**What is out of balance.** The day added a great deal of prose and very little behaviour — defensible
for two landing slices, but session 0024 named the guarded risk as single-instance abstraction
lock-in, and today deepened the documentation of an abstraction (`TimelineProvider`'s fetch unit) that
still has exactly one witness. Prose about an unwitnessed generalization reads as knowledge and is not
yet knowledge.

**What was missing, and got fixed before the day closed.** The carrier had reached the glossary but no
architecture-level map; `/sync-arch` was paused mid-pass for `/review-impl` and then resumed —
`CoverageSet` now appears in the canonical-data-model diagram, its own contract surface, ADR-0001's
closure bullet, and the Provider surface. What remains missing is harder: nothing in-tree authors a
boundless ask, so the whole new arm is exercised only by direct tests, and the shelf that makes its
surplus worth anything is two slices away.

**Hidden edges.** The ∃/∀ ambiguity in an interval label, now written in two places. The
assert-vs-refusal boundary, which reads as a leak to anyone who has not read #21. And "bounded paths
byte-identical", true of the suite but not of one class of direct mixed-parameter asks.

**What would make life easier.** Two of today's threads independently invented the same instinct —
`TODO (temporary)` at a code site, and "name the silence" in the review edits. The edge record has
`⚠ unguarded` for this; code has no marker. One shared convention would make all three greppable.

## Continuation

Closed before the day ended: `/sync-arch` resumed and finished, the slice closed into `done/`, and
[#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)'s "Related
limitation" repaired — the mixed-bounds refusal does **not** dissolve at 006, because the licence is
boundlessness rather than the store, so what 006 supplies is a second kind of ask.

1. **Next implementation action: slice 3**, [retentive timeline Store](../tickets/01-0115.0030-timeline-store.md)
   with [RFC 0013](../rfc/0013-20260808-timeline-store.md), where `assimilate`'s concrete shapes are
   revisited. It is the first slice a caller can observe, because slice 2's widening is inert until a
   store holds the surplus.
2. **[RFC 0011](../rfc/done/0011-20260808-any-boundless-member.md) never moved to `rfc/done`** when
   0115.0010 closed on 08-08, and should. Archiving a document silently breaks every relative link in
   it and every link to it — closing this slice broke about twenty, all now repaired, along with the
   depth drift the 08-06 and 08-08 archivings had already left behind. Every relative link under
   `docs/` now resolves except one in historical session 0023, which stays as written. Worth a check
   whenever a document moves.
3. **One convention worth minting** (from the advisory read): code has no marker for "deliberately
   unguarded, here is why", though the edge record has `⚠ unguarded` and comments now have
   `TODO (temporary)`. Three notations for one instinct.
