# 0038 · 2026-08-22 · The algebra becomes a family, and rolling is one member

**Scope:** [0114](../tickets/done/01-0114-timeline-shape-generalization.md) from the last
pre-implement check through close. Carved the same day at the obs serving plan when a sibling
wrapper was measured at a ~160-line fork; implemented in three green stages; reviewed and
synced. Recorded after a parallel skill-corpus arc had already taken the next session number;
that arc did not cover this ticket.

## Work done

- **Fourth validation pass** before coding: the live member named, `clock` placed on the member,
  `stamp` ordered after `retrieve`, and the fake member required to publish a `ScatterDomain` and
  ground via the matched place's separable stand-in — otherwise an exact `GridDomain` would not
  prove the extension point.
- **Three stages, each green.** Extract `resolve` / `stamp` / `refresh` in place; split
  `RollingTimeline` and change four constructors by class name; guard the family, the scatter fake,
  and a rolling refresh that adds no transport call. Existing Open-Meteo and TWC suites unedited
  beyond construction. 455 deterministic tests.
- **`/review-impl` and `/sync-arch`.** Edge record, module-layout, and the `Provider` ABC docstring
  caught up to the family; architecture already described it.

## Settled this session

- **The live member is `RollingTimeline`** — a continuous footprint whose window rides the clock,
  the same fact `RollingAxis` already names; a name with "forecast" in it would go stale the moment
  archived runs exist → [ticket](../tickets/done/01-0114-timeline-shape-generalization.md),
  [architecture § Provider](../architecture.md#provider-leaf-manifold).
- **`clock` is a member fact**, with cadence and spatial reach. After the split the algebra never
  reads it → [RFC](../rfc/done/01-0114-timeline-shape-generalization.md).
- **`stamp` runs after `retrieve`** — today's interpret-time clock read; stamping first would move
  `fetched_at` / `expiration` by retrieve latency → same RFC.
- **Four answers, three of them new.** `capability` was already abstract on `Provider` and is the
  right home besides: a fetched-facts member must publish one that can change after a refresh →
  [edge/provider.md](../edge/provider.md).
- **Grounding takes engaged parameter ids**, deduped in declaration order — `agreed_geometry`
  returns `members[0]`, and a set would have made Z depend on iteration order → RFC.
- **A sibling wrapper was the wrong cut.** ~160 of ~243 lines are identical for a station producer;
  the four answers are the producer's own facts, not a collaborator → architecture § Provider.

## Found, not settled

- **`__subclasses__()` only sees what is already imported.** The first guard walked the class
  hierarchy and would have passed with an empty family if the vendor modules had not been loaded.
  The close made it load the shipped set and recurse — a guard that guards nothing is a known
  failure mode here (0035's "a guard that guards nothing passes silently"), caught on this ticket
  by review rather than by the first test.
- **The family is fake-tested ahead of its second member**, same shape as the scatter substrate.
  0124.0030 is where `resolve` / `stamp` / `refresh` first meet a real scatter, an `ArchiveAxis`,
  and a registry re-read.

## Open questions

All live in their owning documents; cited, not restated.

- What `refresh` on the request path cannot reach — a request at an unknown place is declined at
  admission, which is sync and precedes `project`, so the refresh cannot rescue it →
  [0124.0030](../tickets/01-0124.0030-station-observation-serving.md) (the bound is recorded in
  the RFC because that is where the `await` was placed).
- Whether archived vendor runs become a thin `stamp` override or a construction fact of the scatter
  member → [0134](../tickets/01-0134-forecast-run-archive-source.md)'s align.
- A gridded or swath delivery still adds its own wrapper; this ticket bought the precedent for
  how *its* members would divide, not code → [edge/provider.md](../edge/provider.md) follow-ups.

## Continuation

1. **0124.0020 — collector transport and decode.** Ready; first real `Closeable` holder; schema
   pinned by fixtures. Implementation is next.
2. **0124.0030** follows, joining this family as the scatter member.

## Advisory read

**What is great.** The serving plan measured the sibling-wrapper alternative instead of following
the architecture's sentence. ~160 duplicated lines is a number, not a taste, and it is why the
family exists. The same pass caught that `ground` refuses a snapped T against non-separable
geometry — the actual reason `resolve` had to be an extension point — and refused a fake that
would not have failed a copied rolling `resolve`.

**What is good enough.** Three stages that each ended green, and a pure refactor whose proof is
the suites that already existed. The new tests pin the family contract, not vendor behaviour.

**What is questionable.** Recording this session a week later, after a different chat had already
taken 0037. 0114 closed the day it landed and had no snapshot until now. The corpus is good at
closing tickets and silent about which closed tickets never got a session.

**What is missing.** The second geometry. Every family promise except "Open-Meteo and TWC still
work" is proven by a fake or by counting that refresh did nothing.

**Hidden edges.** Admission stays sync, so a station added to the collector becomes servable only
via later traffic to known places. That is not a bug in 0114; it is 0124.0030's honest bound, and
it will look like a serving bug the first time someone tests "add a station, request it
immediately."

**What next.** 0124.0020's implementation.
