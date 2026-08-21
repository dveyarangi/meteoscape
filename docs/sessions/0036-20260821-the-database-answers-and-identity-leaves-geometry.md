# 0036 · 2026-08-21 · The database answers, and identity leaves geometry

**Scope:** the Mongo observation source align, run against the **live collector database** rather
than against recollection; the impact trace that split it; and the first slice start-to-finish —
RFC, four validation passes, implementation, review, sync-arch, close. The session's shape: two
long arcs where a design was talked into existence and then talked back out again, each time
because a question exposed that the thing had no consumer.

## Work done

- **0124's align**, opened with the necessity gate passing by citation (v1 stories 17/23), then
  conducted against a live connection to the operator's collector: 63 stations, two obs schemas,
  real units, real cadence, real staleness. Most of layers "decode" and "declare" were *measured*
  instead of decided.
- **An impact trace** that found the dominance fold refuses obs+forecast composition on the first
  shared parameter — before implementation could hit it — and split 0124 into two slices plus a
  new prerequisite ticket ahead of the correction calculator.
- **The scatter substrate**: RFC, four validation passes, implementation (in Cursor), `/review-impl`,
  `/sync-arch`, close. 452 deterministic tests, ruff / format / pyright clean, both doc gates green.
- **A carve ticket minted** for `manifold/domain.py`, whose #22 trigger turned out to have fired
  some time ago without anyone noticing.

## Settled this session

- **Observations do not expire, and the whole archive is in reach** — T is one declared window per
  parameter, `[archive floor, clock.now()]`, with each station's true span answered at serve →
  [0124](../tickets/01-0124-mongo-obs-source.md).
- **Exact-station admission, no epsilon** — a request point is served only where it coincides with a
  registered station; radius serving was rejected for want of a customer → same ticket.
- **`ScatterDomain` is geometry only** — paired X/Y points matched jointly, T and Z shared; CF's
  `timeSeries` rung, sibling to the reserved `CurvilinearDomain`, with the trajectory family
  (aircraft, ships, drifters) fenced off as a distinct representation →
  [ADR-0002](../adr/0002-data-model.md), [glossary](../glossary.md).
- **Identity is provenance's, not geometry's** — `AtomicOrigin` carries optional
  `authority` / `process` / `unit`; `unit` is the instance's identity in the authority's namespace,
  never a value the requester could derive from its own request →
  [ADR-0003](../adr/0003-provenance-and-origin.md).
- **`Capability.origins` publishes declared provenance** — (sub-domain, origin) pairs over the
  reach, so a consumer learns what can be requested *and from whom* before requesting; the
  declaration side of ADR-0003's per-point seam → same ADR,
  [architecture § Contract surfaces](../architecture.md#contract-surfaces).
- **Store presence is profile policy** — the `store is None ⇔ materialized` biconditional is gone; a
  storeless non-materialized producer composes →
  [ADR-0006](../adr/0006-materialization-granularity-and-store-shape.md),
  [ADR-0005](../adr/0005-build-time-composition.md).
- **Metered is a provider property**, never key-existence — the first validation pass caught the
  drafted keyed-as-metered proxy being false on its very first customer → the refusal returns at the
  [ledger](../tickets/01-0130-vendor-call-ledger.md), the binder marking the gap with a TODO.
- **Units arrive canonical from the collector** — measured, so the unit-conversion catalogue's
  trigger did not fire and it slides again → [delivery status](../tickets/README.md).

## Found, not settled

- **A design can be argued into existence by its own vocabulary.** `Site` was minted to carry
  station labels, grew `as_sited`, a `sites` accessor, and a `t_extent`, and was then dissolved
  entirely — not because it was badly built but because each part failed the question *who reads
  this?* The corpus's own rule (a helper is minted with its first caller) caught the accessor; the
  user caught the rest. Vocabulary that sounds right is not evidence of a consumer.
- **The same happened to `Attribution`**, minted as a sub-record and dissolved into three flat
  fields once the question "why a new noun, not provenance?" was put plainly. Both arcs cost most of
  the session's discussion and produced *less* code than the first proposal.
- **Recording ahead of agreement is a failure mode with its own signature.** Three times a
  resolution was written into a ticket while the discussion was still open — a background task
  nobody agreed to, a per-site T nobody proposed, a derivation rule mid-argument. Each was
  retracted. The tell is writing during a turn where the user asked a question rather than gave an
  answer.
- **`concerns.md` drifted under this session's own edits** — settled pressure resolved in place with
  a dated note, decisions recorded where only pressure belongs, tickets cited decoratively. Caught
  by the user, not by a gate; the file's rules are prose in a skill, and nothing checks them.

## Open questions

All live in their owning documents; cited, not restated.

- Where a storeless producer's read-back homogenization lives, and whether mirror-waste becomes a
  warning → [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
- What selects a station group once one network exceeds one offering →
  [#50](../concerns.md#50-observation-network-scale-station-grouping-and-discovery).
- How a shared parameter's reach composes across a past-facing scatter and a forward-facing
  footprint → [0137](../tickets/01-0137-obs-forecast-reach-composition.md), whose align owns the
  [#13](../concerns.md#13-candidate-admission-containment-vs-intersection) /
  [#28](../concerns.md#28-reconciler-interface-selection-ordering-vs-per-cell-fold) fork.
- The multi-station ask and its bundle (scatter-as-request, scatter Coverage, sampler widening) →
  [#12](../concerns.md#12-curvilinear-domains)'s target role.
- Two collector-side asks outside this repository's control: a schema version marker and per-station
  latest-observation times →
  [#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own).

## Continuation

1. **0124.0020 — station serving**: `/plan-impl`, then the source itself. Its fixtures come from the
   live database sampled this session.
2. **The collector database accepts unauthenticated connections on a public IP.** Only reads were
   performed. This is an operational matter for whoever runs the collector, and it is independent of
   the read-only source work.
3. **`uv sync` still unused** — every command ran under `--no-sync`, as in 0032–0035.

## Advisory read

**What is great.** The align stopped guessing and connected to the actual database. Units, cadence,
schema discriminators, staleness, the 30-minute `observed_at` offset, per-station collections — all
became facts within one turn, and two of them (canonical units, per-station layout) contradicted
what the corpus had recorded. The concerns file had *predicted* the schema risk; only the
measurement told us its shape.

**What is good enough.** Four validation passes over one small RFC. They converged — structural
error, then contradiction, then edge semantics, then construction guards and citations — and none
was ceremony. But as 0035 observed about a different plan, the shape stopped moving after the first
pass; what moved was how much was proven rather than assumed.

**What is questionable.** The two dissolution arcs. Both ended correctly and both cost more than
they should have, because the first proposal in each case was *plausible* — a named type carrying
labels, a named record carrying identity — and plausibility survived several turns of scrutiny
before a plain question ("who reads this?", "why a new noun?") ended it. The failure was not
inventing the thing; it was defending it.

**What is out of balance.** The doc-to-code ratio again: ~62 lines of `src` for the substrate
against nine durable documents touched and an RFC amended through four passes. Some is real — the
seam is published and its reasoning must outlive the ticket — but the ratio has now run the same way
for three consecutive tickets, which suggests it is the process's shape rather than any ticket's
accident.

**Hidden edges.** `ScatterDomain` has no serving consumer yet: every promise is fake-tested, exactly
as the ticket asked, which makes 0124.0020 load-bearing in the same way 0124 was for 0116's seam.
And `Capability.origins` is published with **one** declarer and one consumer shape imagined; the
first real edge rendering (0125 or #29's introspection tool) is where its ergonomics get tested.

**What would make my life easier.** A gate for `concerns.md`'s own rules. The doc-integrity gate
catches broken links and unresolved anchors; nothing catches *resolved in place*, *decision recorded
as pressure*, or *decorative ticket citation* — the three drifts this session introduced by hand and
the user caught by reading. Those are mechanically checkable: a `## N.` body containing "settled" or
a date, a ticket link outside a `→ queued as` clause.

**What next.** 0124.0020's `/plan-impl`.
