# 0035 · 2026-08-21 · The seam lands before its holder, and estimates get measured

**Scope:** the v1 contract re-cut and concerns sweep that minted
[0116](../tickets/done/01-0116-composition-lifetime.md), then that ticket start to finish — align,
`/plan-impl` plus three validation passes, implementation, `/review-impl`, and the close. Spans
2026-08-20 into 2026-08-21. The session's shape: almost every turning point came from a claim being
*measured* rather than argued, and most of the measurements contradicted the estimate.

## Work done

- **The v1 contract re-cut** to what nothing else owns (370 lines to 177), a first retirement sweep
  over `concerns.md`, and three missing tickets minted — including 0116, carved out of the Mongo obs
  source so the lifetime seam would be *chosen* rather than invented inside an implementation.
- **0116's align**, run jointly with 0124's as the delivery plan called for. It opened on the
  necessity gate and immediately found the gate's own premise unverified.
- **Resolutions recorded** into architecture § Gateway and its Contract-surfaces row, the glossary,
  [#39](../concerns.md#39-python-embedding-surface-and-public-failures), the embedding Edge record,
  and the ticket — no ADR; the reasoning lives in the RFC.
- **Three `/plan-impl` validation passes.** The second upgraded the weakest stage from inspection to
  an end-to-end proof; the third found two durable docs left contradicting a concern *I* had edited.
- **Implementation, review, close.** 433 deterministic tests, ruff / format / pyright clean, both doc
  gates green. Footprint ~55 lines in `src` against ~130 in tests, plus two file moves.

## Settled this session

- **The driver was never a choice** — Motor reached end of life 2026-05-14, leaving
  `AsyncMongoClient` → [0116 (done)](../tickets/done/01-0116-composition-lifetime.md).
- **Release is required, not tidy** — an async Mongo client binds to one event loop, so "one client
  per application" means one per *loop*, a scope **shorter than the process**; a process-wide cache is
  therefore incorrect, not merely leaky → same ticket.
- **`Gateway` *is* the composition** — permanently 1:1 with its graph, and the surface that must
  perform teardown already holds it, so no second noun and `compose()`'s signature is unchanged →
  [architecture § Gateway](../architecture.md#gateway--caller-policy-boundary).
- **It leaves `api/`** — every surface *receives* a composition and none provides one →
  [module-layout](../module-layout.md); [#39](../concerns.md#39-python-embedding-surface-and-public-failures)
  narrowed to the **name** alone.
- **`Closeable` is a facet, not a third `Manifold` verb** — of nine roadmap items needing winding
  down only four are Manifolds, so a verb buys two mechanisms where one does; it joins `Countable`
  and `Writable` → [glossary](../glossary.md).
- **Structural, so no holder imports it** — `MemoryStore` is the standing proof: a plain class with
  no base satisfying a three-protocol contract. `nodes/` never imports the facet, now or later.
- **One `aclose()`, no `__aenter__`** — `contextlib.aclosing` supplies the with-form, and a `with`
  block whose body is an entire application is the shape ASGI lifespan exists to avoid → ticket.
- **Idempotence by emptying before releasing** — which makes a second call safe after a failure,
  after cancellation, or from another task, with no lock; it retired two constraints the plan had
  merely recorded → [RFC](../rfc/done/01-0116-composition-lifetime.md).
- **Construction stays sync** — the `AsyncMongoClient` constructor is non-blocking and takes no loop,
  so `compose()` never became async. A listed decision that **dissolved** rather than resolving.
- **`HttpxTransport` stays per-call**, with a trigger — the seam lands first, so converting later is
  strictly cheaper than converting now → ticket Out of scope.

## Found, not settled

- **A ticket citing itself is not evidence.** The gate's premise — "a Mongo client must be closed" —
  came from 0116's own ticket, written days earlier in this same corpus. Citing it was circular, and
  only a driver-documentation lookup made it a fact. The corpus is good at recording decisions and
  offers no signal for which recorded sentences were ever *checked*.
- **A plan's cited precedent can silently not apply.** The RFC promised a store-release test
  "injected via a `StoreFactory` subclass, `RecordingStoreFactory` is the existing precedent" — but
  that precedent injects into `Weaver(...)`, and `compose()` constructs its factory internally, on
  purpose, because architecture makes the one-clock invariant structural. The planned test could not
  be written as described. Nothing checks that a precedent a plan leans on transfers.
- **Ticking the acceptance boxes *is* the close.** `test_queue_and_folders_agree` refuses every-box-
  checked outside `done/`, so criteria state is atomic with the mover and the delivery re-cut — not
  something to tidy in passing. Learned by breaking the suite.
- **Two live documents claimed `api/` does not import `nodes/`**, while `mcp_app.py` imports the
  `ParameterTable` and always has. Pre-existing, restated by this change, now stated truthfully with
  the real bound: a surface reaches the algebra, its `Gateway`, and the parameter vocabulary, never
  the graph-building machinery.

## Open questions

All live in their owning documents; cited, not restated.

- The `Gateway` **name**, now that it owns the composition →
  [#39](../concerns.md#39-python-embedding-surface-and-public-failures).
- **Use-after-close** — a released composition still serves, failing *through* the holder as though
  the upstream were at fault; the MCP surface's ref-counted lifespan gives it a concrete instance →
  [#39](../concerns.md#39-python-embedding-surface-and-public-failures) and the RFC.
- **Stateful calculator plugins** would need collecting at the same seam →
  [#26](../concerns.md#26-provider--calculator-plugin-scaffolding).
- **A store's release is unproven end to end** — `stores.created` contributes nothing until a store
  holds something → [persisting Store](../tickets/01-0145-persisting-store.md), where a real
  `SQLiteStore` makes the test need no fake.
- **Whether the seam actually fits its first holder** →
  [Mongo obs source](../tickets/01-0124-mongo-obs-source.md)'s align, which should confirm rather
  than assume.

## Continuation

1. **0124's align** — deferred once when 0116 was carved out of it, and now standing on its own:
   past-facing capability and freshness, how a request point meets a station, and
   [#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)'s
   schema mitigations. Its first fork is stored-vs-storeless, which would fire
   [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization)'s trigger.
2. **Sweep sessions past the rolling window** into `history/2026-08/`.
3. **`uv sync` still unused** — every command this session ran under `--no-sync`, as in 0032–0034.

## Advisory read

**What is great.** The corpus caught four things nobody remembered to check: the conventions gate
caught boxes ticked outside `done/`, the integrity gate held across every doc edit, `/review-impl`
found a docstring asserting a dependency rule the imports contradict, and the align's necessity gate
refused a premise that turned out to be self-citation. None of that depended on vigilance.

**What is good enough.** Three validation passes over one small plan. They were not ceremony — the
second replaced a weak test with a real one, and the third caught inconsistencies introduced by the
recording step itself — but the plan's *shape* never moved after the first pass. What moved was how
much of it was verified rather than assumed, which suggests the passes are really a verification
budget wearing a planning name.

**What is questionable.** Nearly every correction came from the user, not from a skill. The pattern
was consistent and worth naming: *asserting a rule where a measurement was available*. The Mongo
close requirement was recollection. The `aclosing` refactor was cleverness that made the code less
readable and was caught only by someone asking what the code did. The relocation cost was estimated
at a corpus-wide sweep and measured at **five import lines** — an order of magnitude, and it had
already changed a scope decision before anyone checked it.

**What is out of balance.** The doc-to-code ratio inverted again — ~55 lines of `src` against an RFC
amended five times and five durable documents touched. Some of that is real: the seam is published at
0125 and its reasoning must outlive the ticket. But an RFC amended five times before implementation,
then twice more during it, is being written rather than followed.

**Hidden edges.** The seam has **no real holder**. Every promise is proven by fakes, which is exactly
what the ticket asked for and exactly what makes 0124's align load-bearing in a way a normal
dependency is not: if the seam does not fit a pooled Mongo client, the discovery happens at
implementation, and the argument for building the seam first was that implementation must not be
where it is designed.

**What would make life easier.** A cheap habit rather than a new skill: *measure before pricing a
change*. `grep` for the import sites, count them, then decide. The one time it was done here it
reversed a decision that had already been made twice on an estimate.

**What next.** 0124's align.
