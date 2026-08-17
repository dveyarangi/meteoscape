# 0029 · 2026-08-17 · 0119 lands; two review passes and a widened mismatch

**Scope:** the first implementation stretch since 007 closed. A `/recall` that found 0119 planned and
unwritten, one advisory question on the TWC capture, a third validation pass over the RFC, the
implementation itself, then two `/review-impl` passes — the second of which found the half of 0119
that never reached the durable docs.

## Work done

- **`/recall`** — 0119 stage 1 confirmed as next: `satisfied_by` absent from `src`,
  `_required_coverage` still standing, tree green at 308 tests.
- **The TWC capture question answered as advice, not action** — a real capture pins the vendor's
  envelope, which is a different job from the canned generator that pins our decode; one truncated
  fixture earns its place, the 64 KB report does not (its facts are already in RFC 0120).
- **RFC 0119 amended, then a third validation pass** — two corrections that would have produced wrong
  code, three facts upgraded from assumption to verification. Then compacted under `/denoise` when the
  first amendment ran +87 lines for +48 lines of content.
- **0119 implemented** — the predicate pair, the gate rewrite, the serving seam, the `CadenceDef`
  guard, and the records. `_required_coverage` and `_request_t_bounds` are gone.
- **Two `/review-impl` passes** — pass 1 found two hard failures and four doc/code mismatches; pass 2
  found the widened `capability-mismatch`.
- **A `/sync-arch` pass** — which found architecture still describing code 0119 deleted, in a third
  Reservoir passage nobody knew was there.

Footprint: **359 lines** across `src` and `tests` (plus a 140-line predicate test file), against
**165 insertions / 249 deletions** in `docs` — the first stretch in this project where the tree moved
more than the corpus.

## Settled this session

- **The serving-seam check sits on the shared path, not inside the refill branch** — case D is
  *satisfied*, so a warm in-gap ask never refills and a check in that branch would never run for it →
  [RFC 0119 §3](../rfc/done/01-0119-live-window-edge-tolerance.md).
- **The Reservoir asks `matches` for meet-at-all rather than unwrapping intervals** — otherwise
  `_t_extent` keeps its typed narrowing and nothing collapses →
  [reservoir.py](../../src/meteoscape/nodes/reservoir.py) `_missing` / `_reject_unmeetable`.
- **`matches`'s per-kind dispatch *is* the answerability requirement** — a snapped ask negotiates its
  bounds so overlap suffices; an exact ask names cells nothing will clip, so containment is required
  or `resample`'s aligned crop fails uncategorized. Recorded as a guardrail against a future
  "fix" to `intersects` → `_reject_unmeetable` docstring.
- **Concern #22's temporal-read paragraph is closed** — its stated payoff was deleting three
  `type: ignore`s and **zero** remain; what is left is `as_separable` plus a `None`-check written
  twice with different return types → [concerns.md](../concerns.md) (paragraph removed, code marker
  dropped).
- **A `CadenceDef` invariant break raises `ValueError`; the leaf's `build` authors the
  `CompositionError`** — the value object holds both numbers and neither name →
  [edge/provider.md](../edge/provider.md).
- **The boot seam is parse, then join** — checkable from operator input alone is typed settings';
  config *meeting* a catalogue is `CompositionError`'s. A rule needing one number from each side has
  no home in configuration → [architecture.md § Typed config](../architecture.md).
- **`capability-mismatch` covers declared-and-admitted-but-unservable**, not only undeclared →
  [architecture.md § Failure](../architecture.md#failure-nodata-and-availability),
  [glossary](../glossary.md).
- **That widening is a compatible MCP contract addition** — no wired provider can produce it, since
  Open-Meteo's declaration matches its delivery → [edge/mcp.md](../edge/mcp.md).
- **There are three Reservoir passages in architecture.md, not two** — the 08-11 retention pass
  updated the two it knew of, leaving the most precise one still stating `request T ∩ child Reach`,
  which is deleted code. Corrected, and the serving-seam check added to the same sequence →
  [architecture.md](../architecture.md).
- **The `build`-authored `CompositionError` is marked ⚠ unguarded** rather than stated flat — no
  shipped leaf takes a cadence setting, so the promise has no validator until TWC →
  [edge/provider.md](../edge/provider.md).

## Found, not settled — new pressure

- **The edge's absent-parameter derivation is unsound for a capable-but-unservable parameter.**
  `capable ⇒ runtime-failure` picks the wrong reason once a producer can admit an ask it cannot
  serve. It does not bite today only because every parameter shares one T reach, so the whole request
  fails before the edge derives anything → recorded against
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback).
- **Encoding and link integrity are ungated, and both failed today.** A UTF-8 BOM reached `src` and
  broke the store-privacy guard; a `done/` move broke four ticket links; and a re-depth pass injected
  59 invisible `\x01` characters that `grep` and reading both passed. Three defects of one class, all
  caught only by mechanical checks. Still not ticketed →
  [cicd.md](../cicd.md#ci-pipeline).

## Open questions

All live in their owning documents; cited, not restated.

- Per-parameter clock re-read and diverging reaches →
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback).
- Whether any of this narrows [#21](../concerns.md#21-serves-extent-vs-project-crop-ability) — the
  family note says no; the off-phase case is untouched.
- Tick convention → [#48](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick)
  / [0126](../tickets/01-0126-tick-convention-declaration.md), still waiting on TWC.
- Parity enforcement and routing → [#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).
- A configuration edge record, deferred to its owner →
  [0123](../tickets/01-0123-config-secrets-degrade.md).

## Continuation

1. **Land the TWC fixture out of `tmp/`** — truncated to a handful of ticks — before 0120 stage 1.
2. **0120 (TWC as primary)**, whose `build` owes the `CompositionError` wrap decided here.
3. **Sweep session 0026 (08-09) into `history/2026-08/`** — it has aged out of the rolling window.
4. **A CI link + encoding check**, still unticketed and now with three failures behind it.

## Advisory read

**What is great.** The third validation pass earned itself twice over. It caught a check placed
inside the refill branch that would have satisfied its cold-path test while leaving an acceptance
criterion unmet — the exact failure that looks green — and it verified the plan's load-bearing
premise, that a `RollingAxis` survives composition, which had been asserted through two prior passes
without anyone reading `arbiter.py`. Had that been false, the root Reservoir would have taken the
static arm and 0119 would have shipped fixing nothing.

**What is good enough.** The implementation. It follows the RFC closely enough that the review found
no design drift — every finding was either a mechanical artifact or a document that had not caught up.
The test file in particular carries its reasons: case D says *why* refetching moves the window further
away, which is what stops it being "corrected" into overlap later.

**What is questionable.** Two of pass 1's six findings were mine, inherited from my own amendment —
`TODO(#22)` moved onto a site whose premise had dissolved, and a "kind-agnostic" claim about `matches`
that was wrong in the direction I stated. Both were caught, but by the next pass rather than the one
that wrote them. A plan amendment is not self-reviewing.

**What is missing.** Still a running TWC leaf — but for the first time the gap is one ticket wide
rather than one decision wide, and the capture is still on one machine.

**What is out of balance.** Nothing, this stretch — which is itself the observation. Sessions 0027 and
0028 both flagged a documentation-to-code ratio that had run to roughly 2 000 lines against 18. This
session inverted it. The corrective was not discipline; it was the plans finally being executable.

**Hidden edges.** The one that surfaced three times today is that this project's defect-finding
instrument is *reading*, and reading cannot see bytes. A BOM, a control character, and a re-depthed
path all passed visual inspection and `grep`. Every one was caught by a program. The corpus's
cross-referential strength has an encoding-shaped blind spot underneath it.

The second: a doc pass that counts its targets can miss one and record the miscount as fact. The
08-11 retention pass wrote "**both** Reservoir passages now name the predicate" — there were three,
and that sentence then made the gap invisible to two later reviews, because both trusted it. What
found it was reading the code's deleted rule and searching for its text, not reading the docs.

**What would make life easier.** The CI check, now for the third session running — and its scope is
now known precisely: link resolution, control characters, and BOMs, because all three failed here.

**What next.** 0120, with the fixture landed first.
