# 0013 · 2026-07-16 · 003 align — request shaping: `Capability.reach`, window semantics, membership

Continues [session 0012](./0012-20260714-002b-align-derived-wind.md). An `align` pass on
ticket 003 — which the session ended by splitting into
[003a](../tickets/003a-capability-reach.md) (the reach algebra) and
[003b](../tickets/003b-request-shaping.md) (the edge). Opened by repairing **drift in the release
contract**, then split the ticket, then spent its length on one branch — *how does a surface know how
far a profile reaches* — which reversed itself several times before landing. The reversal trail is
recorded below, because most of what was explored is plausible enough to be re-proposed.

## Doc repair (first, before design)

`v1-requirements.md` still claimed the derived wind views carry a **synthetic** provenance — in the
encoding note, the v1 invariants, and **acceptance criterion §9**. Session 0012 reversed that (wind is
a lossless invertible transform, so it **propagates** the provider's atomic origin) and ADR-0003/0004
were updated, but the release contract was not: §9 asserted behaviour `Calculator` deliberately does
not have. Fixed throughout, plus a stale **"All seven"** → **"All eight"** (the parameter table grew
to 6 canonical + 2 derived when `cloud_cover` landed at session 0011).

**Not drift:** session 0012 recorded the kernel as `fn: Coverage → Coverage`; ADR-0004 and the code
say `Coverage → (Domain, ranges)`. The build pass refined it (a kernel holds no `ParameterTable`, so
it cannot author capability). The ADR is current; sessions are historical.

## The decisions

1. **003 sheds the alias / exact-Z half.** The mechanism is already a recorded contract seam
   (architecture.md's Surface adapter "desugars parameter **aliases**"; ADR-0002's request Z modes —
   `VantageAxis` = vantage, `RegularAxis` cell = exact — and "the shape the edge alias table desugars
   to"). What it lacks is a **driver**: `soil_temperature_6cm` is not a v1 parameter,
   `cloud_cover_low` needs the deferred Overlap Calculator, and `temperature_2m` is a **semantic
   no-op** against the count-1 `2 m` declaration (same winner, same values; only the response Z label
   changes). An implementation ticket would add nothing but a **scheduling claim** — the wrong part.
   Dropped outright rather than re-filed: it re-arises from its product point (roadmap Phase 4) with
   no decision to rediscover. *(No new ticket, no `ideas.md` entry — the contract already carries it.)*

2. **`Capability` gains a per-parameter `reach` `Domain`** (→ ADR-0004 amended,
   [#29](../concerns.md#29-narrated-reach-per-axis-join-conservative-on-extent-axes)). It folds by the same
   leaf/composite algebra as `serves`: leaf → its footprint; **derived → per-axis intersection** (a
   Calculator needs *all* its inputs); reservoir → forwards. Three rules keep it honest:
   - **A composite joins per axis, following the request's shape there.** Admission is whole-request
     containment, and a request is a **point** on X/Y/Z but an **interval** on `valid_time`. So point
     axes **union** ("could anything serve here?") and extent axes **intersect** ("is this whole span
     servable?" — one member must contain it all).
   - **Mixed semantics: spatially an outer bound, temporally a guarantee.** The spatial fold drops
     inter-axis correlation — `{Europe × 16 d, Americas × 10 d}` spans the Atlantic — so read it as
     *nothing outside is servable; not everything inside is*. The T intersection is what makes the
     omitted-`end` default admissible wherever the profile serves: at 10 d, Europe is covered by the
     16 d member and the Americas by the 10 d member.
   - **Advisory, never authoritative.** `serves` stays the sole admission authority; `reach` must
     never feed an admission path.

   **The T fold under-promises, and is deliberately left that way.** Where a member is spatially
   universal (OM global × 16 d + TWC × 10 d) intersection yields 10 d though OM serves 16 d
   everywhere. Accepted: a surface promising 10 days of fully-served coverage is a *correct* product
   statement, callers can still request more explicitly, and a longer product is another surface. The
   named lever if it ever needs addressing is a config declaration — marking a provider explicitly
   **fallback**, excluding it from the reach promise — not location-aware machinery. This is also
   where the abandoned quality/reach distinction lands honestly: the conservative fold *is* a
   quality-inflected promise, stated as what the surface delivers rather than where quality changes.

   This **cashes a dangling claim**: ADR-0004 said an introspection envelope "aggregates from leaf
   reach", but leaf footprints are private to `serves`, so no accessor existed and the aggregation had
   no path. The amendment states the discipline directly rather than enforcing it by omission.

3. **One reach — quality is not a capability.** Intermediate drafts narrated a quality/completeness
   pair (see the trail below). Dropped because **quality is a policy outcome**: capability answers
   *can you serve this*, quality answers *how well did it go* — which the response already reports per
   parameter via provenance. Every objection raised against a narrated quality boundary was one error
   in four costumes: it leaked priority ordering ([#7](../concerns.md#7-quality-scoring)), its meaning
   flipped with the reconciler mode, it was unverifiable through `serves` (`any(...)` answers
   *whether*, never *who*), and it gave the agent no decision procedure. A deployment that sells
   quality tiers expresses them as **separate profiles behind separate tools** — the sibling-tool
   precedent already set for a daily product (session 0009), not a modulation of one tool.

4. **Omitting `end` runs to the reach end; `Settings.default_horizon` is deleted.** When the caller
   does not say how far, they get what the profile serves. Because `RollingAxis.extent` resolves
   against the clock, reading reach **live at request time** gives the exact footprint end, so the
   default request is admissible **by construction**. The reach end is **absolute, not a length from
   `start`** — given `start`, it clips the beginning and does not shift the end (a length reading
   overshoots whenever `start` is in the future). Degenerate case (`start` past the reach end): build a
   **single tick at `start`** and let admission answer; the edge must not pre-reject, because the T
   fold is conservative and a `start` past it may still be servable.
   *Accepted consequence:* v1's default response becomes ~16 days (384 ticks × 6 params ≈ 22 KB). The
   client can always request less; the alternative was re-introducing an arbitrary number.

5. **Out-of-envelope windows resolve as `capability-mismatch`, never edge validation.** Past `start` /
   over-horizon `end` build a well-formed Selection and fail **admission**. The edge cannot state the
   boundary correctly anyway: the true left edge is the **run anchor** `A = floor(now − L, Δ)`, not
   "now", so an edge check would falsely reject `start = 11:00` at 12:30. Honest to the future — a
   historical producer makes yesterday servable with **zero edge changes**. `bad-request` stays
   reserved for windows malformed **in themselves** (unparsable, `start > end`). Clamping declined
   (silent request mutation). No max-window guard — reach bounds it, and an axis is
   `anchor + step + count`, so an absurd `count` costs O(1) before admission rejects it.

6. **Window → lattice semantics.** Naive ISO → **UTC** (rejecting naive buys correctness-theatre
   against agents that emit it constantly), offset-aware converted. `start` → **floor** to the hour
   (the tick whose cell contains it; `ceil` would silently drop the time asked for). `end`
   **inclusive**, same flooring — so **`start == end` yields one tick**, giving "current conditions"
   for free. Omitted `start` → `floor(now, 1h)`. **A bare date means the day it names**
   (`end="2026-07-20"` → through the 23:00 tick): the inclusive-`end` rule at the granularity the
   caller supplied, since a date is a day-cell. Midnight-reading was rejected because "through the
   20th" would silently return one hour of it.

7. **Per-parameter reach is never a request axis.** Session 0009's decline of per-parameter domains
   (reaffirmed 0011) settles it: one-domain `Selection`, one window. A profile is **demand-coherent** —
   a client's business logic wants one window; different logics get different profiles. Divergence
   surfaces as **outcome** (per-parameter dropout with reasons, 009) and, when structural, as
   **introspection** — never as a per-parameter window in the request.

8. **No response-size narration.** Token counts are tokenizer-dependent and approximate; the shape is
   already derivable (hourly × window × parameters) and bounded by reach. The lever for a long window
   without the tick count is the **`forecast_daily` sibling tool** (session 0009), not a `step` knob.

## Second doc-debt find: the undeclared NaN nodata path (→ ticket 002c)

Raised late in the session, and it is a *different* shape from the provenance drift above — not a doc
that fell behind the code, but an **unstated assumption with a silent fallback**:

- **ADR-0002 / architecture** fix nodata as an explicit `present` mask and **reject a NaN sentinel by
  name** (dtype-agnostic; keeps "no data" distinct from a legitimate not-a-number value).
- **Session 0011** specified the Provider side to match: `decode(arrays) → (values, present)`.
- **The 002 build** shipped `Decode → list[float]`, with `cell()` mapping vendor null → `nan` and
  `open_meteo.project` hardcoding `present=None` — and a **docstring blessing it** ("None cells stay
  None → nan"), so it does not read as a defect.
- **v1-requirements** said "Every atomic `ParameterData` carries `present = None`", which made the
  code *look* conformant while leaving unstated *why* (complete vendor series) and *what happens
  otherwise*.

Consequences: the serializer's `null` branch requires `present is not None`, so it is **dead for every
real response**; a vendor null reaches the wire as `NaN`, which is **not valid JSON**; and the one
nodata test hand-builds `present` on a fabricated Coverage, so it is green over a dead branch.

**Resolution:** build the mask (option b) rather than treating a null as `runtime-failure` (option a).
Option (a) is cheaper and conforms to the taxonomy, but a real vendor does occasionally null a cell,
and failing a parameter over one absent hour is a worse product than reporting the successful gap it
is. The usual "no driver" argument does not apply — the driver exists, it was just masked by NaN.

**Placement reasoning** (the general shape for doc-debt items): roadmap **Phase 1**, which scopes the
error/nodata taxonomy and where the failure is live in the core answer path — not Phase 2's
operational substrate. Doc home **`v1-requirements`**, whose job is v1's positions on contract seams;
the `present = None` assertion is now qualified as the *elided all-present case* rather than a claim
that gaps cannot occur. Work owner **[ticket 002c](../tickets/done/002c-provider-nodata-mask.md)** — 002's
unfinished business (002 specified it, the build missed it), the same relationship 002b had to 002,
and a **blocker for 009**, whose nodata-vs-failure distinction assumes the mask exists.

## Third doc-debt find: the unmodeled `vertical_reference` (no ticket — deliberately)

Same report shape as 002c ("contract requires X, code lacks X, status says done"), **different
resolution** — and the contrast is the useful part.

[ADR-0002](../adr/0002-data-model.md) requires the Z axis to carry one axis-level
**`vertical_reference`** (`above_ground` / `isobaric` / `height_above_msl`); `architecture.md` and the
glossary echo it. The implementation has **no such property anywhere** — `Axis` declares itself "pure
geometry", `GridDomain` carries only axes, and `vertical_reference` appears **zero times** in `src/`.

But v1 is **single-frame**: every Z declaration (2 m, 10 m, surface, `[0, TOA]`) is `above_ground`. So
the attribute would be a constant nothing reads, and **no v1 behaviour is wrong**. That is the
discriminator against 002c:

> **Does the gap produce wrong behaviour today?** 002c did — a vendor null reached the wire as `NaN`,
> invalid JSON. This one does not; it is a **dormant slot**, correct-by-accident because only one
> frame exists.

So it resolves to a **declared position with a named precondition, not a ticket**: recorded in
`v1-requirements`' deferrals, because no roadmap phase introduces a second frame — the trigger is the
first second-frame *parameter* (soil depth, isobaric, flight levels), and building the slot belongs to
that ticket. The hazard it guards is specific: Z admission compares extents **numerically**, so
without the tag `1000 hPa` matches `1000 m above ground` — precisely the cross-frame nonsense ADR-0002
rules out. Not filed as a concern: `concerns.md` owns *unresolved design pressure*, and this design is
fully resolved — only unbuilt.

## Fourth doc-debt find: unenforced range/domain alignment (→ folded into 002c)

> **Superseded (session 0014).** The fold was reversed on re-align: `ParameterData` took ownership of
> `present`'s length, which removed this section's load-bearing argument, and no construction site was
> found that can misalign today — including `Calculator`, whose only kernel is pointwise. Now
> [concern #31](../concerns.md#31-positional-alignment-is-asserted-never-checked). The reasoning below
> is kept as the trail.

[ADR-0004](../adr/0004-producer-resolution-and-capability.md) requires a Calculator node to validate
its kernel's payload — `ranges` keyed by the declared output group **and aligned to the returned
`Domain`**, "a build/derivation failure, not silent corruption". `Calculator.project` checks the keys
and **not** the alignment.

Investigating widened it: the invariant is **stated on the type but enforced by callers**.
`CoverageRecord`'s docstring asserts "`ranges` are positional to `domain`" while the dataclass
validates nothing; there are **five** construction sites (`sampling`, `arbiter`, `calculator`, two in
`open_meteo`); `open_meteo` hand-rolls the length check **three times**; `Calculator` does none.

Nothing is wrong today — the wind kernel zips `strict=True`, derives `present` at `len(cov.domain)`,
and returns its input domain unchanged, so it cannot emit a misaligned range. By the 002c/vertical
discriminator this is **dormant**. But it differs from the vertical-reference case in two ways that
change the disposition: the fix is **one `__post_init__`** rather than a change to every construction
site, and **002c makes the invariant load-bearing** — `present` stops being always-`None` and becomes a
real array that must align with `values` *and* the domain.

So: **folded into [002c](../tickets/done/002c-provider-nodata-mask.md)** rather than given its own ticket,
and fixed on the **type** rather than in `Calculator`. That covers all five sites at once, satisfies
ADR-0004's node requirement as a consequence, and follows the architecture's own "deep modules"
principle instead of asking every caller to remember. The failure it prevents is the bad kind: a
misaligned range serializes as a `values` array of different length from `valid_time`, so the agent
reads values against the wrong timestamps — silently.

## Fifth doc-debt find → a real design gap: `ANY` axes and shape-correspondence

Reported as "the native-record transport contract is incomplete": architecture.md gives the Provider
contract as `project(Selection) -> Manifold` (singular, :257) while describing the Provider as
returning **native records** (plural, :201/:271), with no carrier for the plural. Verified, and the
code splits the difference — `open_meteo.project` ends in `_assemble(records, selection)`, a
self-labelled "interim fold", which is also ADR-0006's **rejected** "flatten per fetch" option.

**The align went through four wrong answers before the right one**, and the trail is worth keeping:

1. *Wrap the records in a Manifold and return that.* Dead — **ADR-0001:20**: "sampling is just
   `project` with an **enumerable** Selection", and **ADR-0002:175**: a `project(sel)` returns "a
   Coverage on `sel.domain`". The Reservoir's ask is enumerable, so the answer **must** be co-domained
   on it. `_assemble` is not a shortcut — it is the invariant being honoured.
2. *Have the Arbiter, or the store, ask per parameter group.* Dead — that is the caller
   pre-partitioning, and each ask that reaches the Provider is a **vendor fetch**: four groups, four
   HTTP calls for data one call returns.
3. *Make `Selection` per-parameter.* Rejected on merit (not on session 0009's precedent, which was
   argued against a need — exact-Z aliases — that 003 has since dropped): it does not remove the
   partition, it **relocates it upward** into `Coverage`, the Arbiter's single target lattice, and the
   serializer's shared `valid_time`.
4. *An "ANY" **Selection mode**.* Nearly right, but too coarse — X/Y cannot be `ANY` for a point
   vendor, so the abdication is **per axis**.

**The resolution (the user's, arrived at by pressing on all four):**

- **`ANY` is a general axis kind** — "answer this axis at your native cells" — and it is the **limit
  case of `quantize`'s widening**, not new machinery.
- **Which axes are `ANY` derives from the store's assimilable unit**: an axis is `ANY` exactly when
  the unit spans it entirely. Timeline store → `T`, `Z` `ANY`, `X/Y` snapped; grid store inverts it.
  So nothing is vertical- or timeline-specific and the Source stays generic.
- **Closure is shape-correspondence**: the answer mirrors the question. Fully enumerable → co-domained
  `Coverage`; `ANY`-bearing and multi-parameter → legitimately **multi-domain**. The partition is
  legal *because it was asked for*.
- **The Provider is asked once** — multiple asks multiply vendor cost.
- **The store slices the answer** (tentative, revisit at 006): only it holds both halves of each unit
  `Selection` — `X/Y`+`T` from its private lattice, the native cell from the answer.

**Homogenization is unchanged.** `ANY` only widens the stored extent further; read-back still crops or
relabels each axis back onto the request, which is `quantize`'s documented "opposite directions"
mechanic.

Also corrected en route: I invented a `Store.report()` method with bespoke types. There is none —
**held** is the store's own `capability` ([store.py:36](../../src/meteoscape/nodes/store.py)) and
**fresh** is `expiration > now` off the provenance `summary`; ADR-0001 says outright that "the algebra
needs no `is_current` operation". I also called the per-unit staleness granularity an open question
for 006; ADR-0003 already fixes it as **per-parameter**.

## The reversal trail (recorded so it is not re-proposed)

The reach branch passed through four positions before landing on decision 2. Each was rejected for a
reason worth keeping:

1. **Probe the composite `serves`** to recover a scalar horizon — rejected: `UnionCapability.serves`
   is `any(...)`, so it is **priority-blind** and cannot express anything about *which* producer
   answers. Also inverts a predicate to recover a value it was never asked to carry.
2. **Declaration-derived at composition** (`OfferingSpec.cadence` + `OfferingDef.priority` +
   parameter sets + `ArbiterPolicy`), with `CadenceDef` hoisted onto `OfferingSpec` — rejected once
   the product collapsed to one reach: it duplicates a derivation the capability already performs,
   needs a consistency test to catch drift, re-implements `DerivedCapability`'s input-intersection
   outside it, and threads the reconciler mode by hand. All four dissolve when reach folds off the
   capability, which encodes the admission semantics already.
3. **A three-boundary envelope** (full-bundle / preferred / max) — `max` rejected as **existential**
   ("*something* reaches this far"), unusable without knowing *which*, and **over-promising** where the
   others under-promise. Rule extracted: *a description string carries universals only.*
4. **A two-boundary envelope** (quality / full) — rejected per decision 3.

Also corrected mid-session: an earlier draft claimed the boundaries were **mode-invariant**. False —
under `priority` a window must fit **one** producer, under amendment the **union**, and the two give
different values. Moot under decision 2 (the capability composite carries the mode), but the reasoning
is why "mode is an input" kept resurfacing.

## Layer distinction that unlocked it (grilling artefact)

Three policies had been bleeding together; separating them dissolved most of the argument:

- **Fallback** — *who serves a parameter* (the reconciler's; wholesale, one winner).
- **Membership** — *what a beyond-reach request gets* (→ [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback)).
- **Narration** — *what the client is told up front* (→ [#29](../concerns.md#29-narrated-reach-per-axis-join-conservative-on-extent-axes)).

The **ordering asymmetry** — **under `priority` mode** — is why only one direction leaves residue:
admission compares a candidate's reach to the **request**, not to the primary. A **longer** fallback is
admitted wherever the primary was and further — it substitutes **wholesale**, the answer is complete,
only quality changes. A **shorter** fallback is admitted only within its own reach, so fall-through is
unavailable **exactly on the long requests where a primary fault hurts most**.

That residue is a **mode artifact, not a standing defect**: whole-request containment filters the
partial producer out before the reconciler sees it. Under amendment/splice the shorter fallback is
admitted by intersection and contributes. So **the mode that fixes #30 is the mode padding needs** —
padding is a *consequence* of the #13/#28 widening (plus a per-cell reason channel), not a rival to
it. What stays open is only whether a profile *stuck on* `priority` deserves a padded tail.

## Cases dissolved under grilling (recorded so 004 does not re-derive them)

- **Single-vendor short parameter (005)** — *not* supply-imposed heterogeneity. The operator bundles
  knowing what the market serves: if soil moisture reaches 7 days, the agriculture profile **is** a
  7-day product. Supply constrains *where the boundary sits*, not the bundle's coherence.
- **Nowcast blend (radar + NWP)** — a **taxonomy error**. Radar is not a fallback for a 16-day
  request; the model **amends** the radar, both contributing to one `ParameterData` per cell. That is
  the coverage reconciler (#28 / the recorded "obs + forecast along `valid_time`" extension point),
  not fallback.
- **Archive breadth** — decades-long fetches are **batched**, so padding payload never arises; and the
  right policy there is **strict** (a 50-year series with a parameter silently missing is a corrupted
  dataset, not a partial answer).
- **Profile-kind taxonomy** — an attempt to multiply objectives (comparison / consensus / uncertainty
  / verification) against temporal orientation was **wrong**: those objectives differ in **provenance
  and response content**, not in what you can ask for, so they add **zero** envelope facets. Only
  temporal orientation matters, and only the forecast arm has a degrading reach at all.
- **Residue, a different problem**: a station that began measuring humidity in 2003 inside a 1990–2020
  request is **intra-parameter temporal availability** — genuine nodata plus a *slice-extraction*
  (introspection) need, not a response-shape question.

## Docs updated with this session

- **ADR-0001** — closure restated as **shape-correspondence** (the answer mirrors the question's
  shape); `ANY` named as the limit case of `quantize`'s widening.
- **ADR-0002** — the unqualified *"`project(sel)` always returns a Coverage on `sel.domain`"* gains its
  **enumerable** qualifier; `ANY` added as a general axis kind, derived from the unit definition.
- **ADR-0006** — the partition reaches the store because the **question asks `ANY`**; one fetch, not
  per-group; `assimilate` consumes the **answer** and samples units (the store slices, tentatively);
  `quantize`'s third per-axis case.
- **ADR-0004** — amended: `Capability` publishes an **advisory per-parameter `reach` `Domain`** with
  its fold rules and the outer-bound / never-authoritative discipline; supersedes the accessor-less
  "aggregates from leaf reach" note. The `serves` path still synthesises no `Domain`.
- **`architecture.md`** — Capability contract surface gains `reach` (advisory, non-admission);
  concerns index gains #29 / #30. The Catalogues bullet is **unchanged** (the `CadenceDef` hoist was
  explored and dropped).
- **`concerns.md`** — **#29** (narrated reach: per-axis join, conservative on extent axes) and **#30** (response
  membership under runtime-degraded fallback, low priority).
- **`glossary.md`** — **Reach** (per-Parameter Domain, per-axis join, never an admission input) and
  **Envelope**; `Capability` entry updated.
- **`v1-requirements.md`** — provenance drift repaired (propagate, not synthesize) across the encoding
  note, invariants, invariant title, acceptance §9, and the deferred list; "All seven" → "All eight";
  user stories 3 and 10 and the Time-axis envelope bullet rewritten around reach; no configured
  default horizon.
- **ticket 003 split** into **003a** (`Capability.reach` — per-axis folds + the `Interval` union /
  intersection algebra; algebra-level, no surface change, status **Ready**) and **003b** (request
  shaping at the edge — free windows, reach-based narration and defaults; status **Partial**, since
  the Phase C bits landed there). The split follows the dependency: geometry → capability → edge, and
  it clarifies status, which had been doing double duty. 003a carries the geometry concern cluster
  (#22 module split, #23 axis types, #12 `intersect` seam, #13 as a future consumer).
- **ticket 003b** — outcome / What-to-build / window semantics / AC rewritten around `Capability.reach`;
  alias half dropped with rationale; out-of-envelope → `capability-mismatch`.
- **ticket 002c** (new) — Provider nodata mask: `decode → (values, present)`, vendor null →
  `present[i] = False` → JSON `null`; retires the NaN substitution. Also centralizes the positional
  values/present/domain invariant on `CoverageRecord.__post_init__`, closing ADR-0004's unimplemented
  Calculator alignment check. *(The alignment half was reversed at session 0014 → concern #31; the
  ticket now scopes to the nodata mask and moves presence behind `ParameterData` behaviour.)*
- **`v1-requirements`** — parameter-encoding note rewritten around the `present` mask (with
  `present = None` qualified as the *elided all-present case*); deferrals gain the **unmodeled
  `vertical_reference`** entry with its second-frame precondition.
- **tickets/README** — the "Canonical v1 parameter set: Done" row now names both unbuilt contract
  slots (nodata mask, `vertical_reference`) instead of reading as fully delivered.
- **ticket 006** — gains `quantize`'s `ANY` axes, the one-fetch multi-domain answer, store-side
  slicing, and retirement of the eager provider-side flatten; four new acceptance criteria.
- **ticket 009** — scope note: fall-through reaches only **admitted** candidates, so a shorter
  fallback is unreachable past its own reach; omission + reason is the terminus → #30. Also corrected
  the false "nodata → `null` serialization already landed" claim (the branch is unreachable until
  002c) and added 002c as a dependency.
- **tickets/README** — 003 row and the free-windows capability row realigned.

## Open / continuation

- **003a implementation deltas** (algebra only, no surface change):
  - **Per-axis `Interval` union / intersection** — `domain.py` lists `intersect` as a *declared seam*,
    not built. Geometry-core work; property-test both coordinate kinds (`float`, `datetime`), empty
    and touching cases. Decide #22 (carve `lattice.py`?) and #23 (split the axis types?) here rather
    than compounding them silently.
  - **`Capability.reach`** on the protocol + all four implementations
    (`FootprintCapability`, `EnumerableCapability`, `UnionCapability`, `DerivedCapability`) and the
    `Reservoir` forward, with the **per-axis join** (point axes union, extent axes intersect).
  - Assert **no admission path consults `reach`**; `serves` behaviour unchanged.
- **003b implementation deltas** (the edge, on top of 003a):
  - **Free window**: parse (naive→UTC, date-as-day), floor `start`, inclusive `end`; omitted `end` →
    live reach end (absolute, clipping); degenerate `start` → single tick. Retire the `start`/`end` →
    `bad-request` stub. Open-Meteo's fetch already maps `t_extent` → `start_hour`/`end_hour`.
  - **Delete `Settings.default_horizon`** and its threading through `server.py` / `build_mcp_app`.
  - **Narration** reads reach off `gateway.best_view.capability` (the edge already holds it for
    `parameters`); the `min`-over-exposed-parameters fold stays at the edge.
  - **Out-of-envelope** rides admission; no edge guard, no pre-rejection against `reach`.
- **Deferred seams named here:** regional providers (reach genuinely varies by lat/lon → the
  capabilities-introspection tool, which can return structure a static string cannot); nodata-padding
  (**worth it, low priority** — needs #13 + #28 + a per-cell reason channel); backward reach for
  historical provision (should absorb into `reach` without a contract change, since it is a `Domain`).
- **Watch at 003b build:** free windows are the first requests to leave the fixed hourly on-lattice
  shape, so [#21](../concerns.md#21-serves-reach-vs-project-crop-ability) (`serves` admits by extent
  while the sampling engine only crops aligned identical-step lattices) stops being theoretical —
  flooring `start` to the hour keeps requests on-phase, which is what holds it at bay.
- **003 align is complete** — both halves are ready for the build pass, 003a first.
