# Composition lifetime and shutdown — implementation plan

**Authored:** 2026-08-20

**Last amended:** 2026-08-21 — the store half's release proof defers to
[0145](../../tickets/01-0145-persisting-store.md), where a real `Closeable` store makes it natural;
`aclose()` empties its list before releasing, which retires two standing constraints; FastMCP's
ref-counted lifespan and its un-entered-lifespan guard recorded (fact 3). Earlier the same day:
`gateway.py` moved out of `api/` and absorbed the facet, answering the placement half of #39 while
leaving the name to 0125.

Implements [composition lifetime and shutdown](../../tickets/done/01-0116-composition-lifetime.md), whose
align resolutions this plan takes as given; the durable contract is
[architecture § Gateway](../../architecture.md#gateway--caller-policy-boundary) and the
[`Closeable`](../../glossary.md) glossary entry.

## What is being built

One way to release what a composed profile opened. Today nothing in `src` owns a resource outliving
a call — `grep` for `aclose`, `__aenter__`, `async def close` returns nothing — and `compose()` hands
back a `Gateway` with no way to let go of anything.

After this ticket the graph still holds nothing: **no shipped producer or store is `Closeable`**.
`MemoryStore` holds memory, and every Provider builds a per-call `httpx.AsyncClient`. The seam is
built ahead of its first `Closeable` deliberately, because the two that arrive do so in tickets that
must not each invent it — the [Mongo obs source](../../tickets/01-0124-mongo-obs-source.md)'s pooled client and
the [persisting Store](../../tickets/01-0145-persisting-store.md)'s substrate connection. Every promise
below is therefore proven by fakes, which is what the ticket's criteria ask for.

## Load-bearing facts

Verified in code or in the driver's documentation; the plan depends on each.

1. **Relocating `gateway.py` out of `api/` costs 5 import lines.** Measured: `api/mcp_app.py` and
   `server.py` in `src`, three test modules, plus moving `tests/deterministic/api/test_gateway.py` up
   to mirror `src`, and `api/__init__.py`'s docstring, which claims the package *applies caller
   policy* — the one thing that leaves with `Gateway`. **Only `module-layout.md` names the
   placement** (`api/  # gateway + mcp_app`), which stage 4 rewrites; no other live document does.
   The expensive part of the [#39](../../concerns.md#39-python-embedding-surface-and-public-failures)
   question is the **rename** (glossary, architecture, three Edge records, ADR text, code, tests);
   the *placement* half is separable and cheap, and the align's reasoning already settled it —
   surfaces **consume** the composition, they do not provide it, so a type every surface receives is
   not a surface-layer type. `nodes/` never imports `api/` (grep: zero hits) and will not import
   `gateway.py` either (fact 8), so the move breaks nothing beneath it.
2. **Teardown cannot happen after `app.run()` returns.** `app.run()` creates and destroys the event
   loop; an `AsyncMongoClient` binds to one loop and
   [cannot be shared across loops](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/),
   so `asyncio.run(gateway.aclose())` after the server stops would close a client against a dead
   loop. **The lifespan hook is required, not stylistic.**
3. **FastMCP enters the lifespan inside the loop, and shields its exit from cancellation.**
   `run_stdio_async` wraps the whole run in `async with self._lifespan_manager()`
   (`fastmcp/server/mixins/transport.py:207`); the HTTP path does the same at `:299`, so
   [0165](../../tickets/01-0165-rest-surface.md) inherits a working hook. `FastMCP.__init__` takes
   `lifespan` (`server.py:305`), the manager enters it and sets `_lifespan_result_set` — so yielding
   `None` is fine — and unwinds under `anyio.CancelScope(shield=True)`, whose comment names
   *"closing DB connections, flushing buffers"* as the reason. **Release therefore survives Ctrl-C**,
   which is what makes "the shipped server releases what it composed when it stops" true for the way
   an MCP stdio server actually stops. The manager is also **ref-counted**
   (`mixins/lifespan.py:189-206`): the first entry runs the lifespan, nested entries only increment,
   and teardown fires on the last exit, which resets it — so the stdio server enters once for the
   process while an in-memory `Client` enters per session, making **idempotence something the shipped
   surface relies on**, not only an embedder's test fixture. Registering a lifespan additionally arms
   a guard: `_lifespan_proxy` (`server.py:265-275`) raises when a custom lifespan exists but the
   manager was never entered, where the default one yields silently. Nothing here meets it —
   `app.get_tool` never runs the low-level server, and every `Client(app)` enters (fact 6) — and
   [0165](../../tickets/01-0165-rest-surface.md) inherits the guard along with the hook.
4. **`Gateway(...)` is constructed at 9 test sites with one argument**, so what is added must be
   optional — varargs is, naturally; otherwise stage 1 goes red for reasons unrelated to what it
   proves.
5. **Providers and Stores have exactly two construction sites** — `manifest.build(...)` inside
   `SourceBinder.build`, and `stores.create(...)` inside `StoreFactory`. Nothing else builds either.
6. **The in-memory `Client` enters the server's lifespan.** `FastMCPTransport.connect_session` wraps
   the session in `_enter_server_lifespan` → `server._lifespan_manager()`
   (`fastmcp/client/transports/memory.py:64,110`), and its comment requires the lifespan to be the
   **outer** context so the session drains before teardown. `test_mcp_app.py` already uses
   `async with Client(app)` at three sites, so stage 3 is provable end to end rather than by
   inspection.
7. **Store creation order is inside-out.** `weave` builds source stores (via `_weave_providers`),
   then stored-calculator stores, and creates the **root store last** — it is the first argument of
   the returned `Reservoir(...)`. Reversing therefore releases root → calculator → source, which is
   outermost-first, so LIFO is a principled order here rather than a convention borrowed from
   `ExitStack`.
8. **A `Closeable` never imports the facet** — and the codebase already proves it. `class MemoryStore:`
   is a **plain class with no base**, yet satisfies `Store`, itself
   `class Store(Manifold, Writable, Protocol)`; it sits in the same module as `Writable` and still
   does not inherit it. Protocols here are structural (PEP 544), not nominal, so a `SQLiteStore` or a
   Mongo provider gains release by defining `aclose()` and importing nothing. Combined with `StoreFactory`
   remembering rather than filtering, **`nodes/` never imports `gateway.py` at all** — now or once
   something starts holding — leaving `server.py` and `api/mcp_app.py` as its only importers. That is the check
   on whether the facet sits in the right place: a lifetime seam that forced every node to import it
   would be the rejected `Manifold`-verb design under another name. It is also what makes fact 1's
   relocation safe, and what lets the facet live beside `Gateway` instead of in a Tier-0 leaf of its
   own.

## The shape

Fact 5 is what keeps this small: `compose` can already see everything the profile built, through the
registry it built and the factory it constructed. **`Weaver` and `wire_source` do not change**, which also means
the 7 `Weaver(...)` and 1 `wire_source(...)` test sites stay untouched.

**`gateway.py` moves from `api/` to the top level**, beside `config.py` and `observability.py`, and
carries the facet with it — one module holding the composition, what it releases, and how those are
found (fact 1). A caller hands over whole **construction sites** and the boundary filters them
**structurally**, which is what `Closeable` *is*: the genericity is honest rather than lax,
`StoreFactory` never needs to know what `Closeable` means, and the `isinstance` test exists in
exactly one place — behind `Gateway`, not in front of it, so no caller can be handed the question.

```python
# gateway.py — top level; imports manifold, imports no surface
@runtime_checkable
class Closeable(Protocol):
    async def aclose(self) -> None: ...


class Gateway:
    def __init__(self, best_view: Manifold, *sites: Iterable[object]) -> None:
        self.best_view = best_view
        self._closeables = tuple(          # one group per construction site, in construction order
            built for site in sites for built in site if isinstance(built, Closeable)
        )

    async def resolve(self, selection: Selection) -> Coverage: ...   # unchanged

    async def aclose(self) -> None:
        closeables = self._closeables
        self._closeables = ()                         # emptied before anything is awaited
        failures: list[Exception] = []
        for closeable in reversed(closeables):        # unwind in reverse of construction
            try:
                await closeable.aclose()
            except Exception as failure:              # one failure must not strand the rest
                failures.append(failure)
        if failures:
            raise ExceptionGroup("composition teardown failed", failures)
```

*Rejected:* a separate Tier-0 `lifecycle.py` for the facet and collector. With `Gateway` outside
`api/`, nothing forces the facet into a leaf of its own, and a two-symbol module justified mainly by
realizers that do not exist yet is a module looking for a reason. Also rejected: a **public**
collector the composition root calls before constructing the `Gateway` — the root would then run the
boundary's own logic and hand back the answer, leaving `Closeable` a name callers must know. Also
rejected: handing `Gateway` the `SourceRegistry` and `StoreFactory` themselves — better types, but
`gateway.py` would import `nodes/`, inverting the one property (fact 8) that lets `server.py` and
every embedder import it without dragging the engine's interior along.

```python
# server.py — compose names where things are built; gateway.py decides which of them qualify
stores = StoreFactory(clock)
woven = Weaver(stores, clock).weave(ProfileDef(...))
return Gateway(woven, sources.providers, stores.created)
```

Naming the two construction sites is the composition root's job (fact 5), so it stays here; deciding
what qualifies is the facet's, so that moved. Each site answers for itself in build order —
`SourceRegistry.providers` beside `StoreFactory.created` — so the root reaches into neither.

Construction order is providers, then stores; `reversed` releases stores first, and within them
root → calculator → source (fact 7). That is outermost-first, so the unwind is principled rather than
borrowed convention — though nothing currently depends on another, so nothing yet *requires* it.

### Who closes it

`build_mcp_app` registers the lifespan itself, and a teardown failure **propagates**:

```python
# api/mcp_app.py
@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
    try:
        yield                     # the server runs here
    finally:
        await gateway.aclose()    # ...and is released when it stops

mcp: FastMCP = FastMCP("meteoscape", lifespan=_lifespan)
```

The unused `_server` parameter is **FastMCP's callback contract, not ours**: the manager invokes
`self._lifespan(self)` (`fastmcp/server/mixins/lifespan.py:214`), passing the server, exactly as its
own `default_lifespan(server)` is shaped. The underscore marks a parameter the caller requires and
this function does not read.

*`contextlib.aclosing(gateway)` would be behaviourally identical and was tried; it is not used here.
`try/finally` around `yield` is the canonical idiom in a lifespan generator and shows the ordering on
screen, and the `aclosing` form saves no lines. The argument that stdlib supplies the with-form
belongs where it was made — deciding not to ship `__aenter__` / `__aexit__` on the public `Gateway` —
and does not extend to a single internal call site.*

**This wrapper stays in `api/`, not beside the facet — and the reason is a product promise, not a
layering rule.** `fastmcp` is imported by exactly one file in `src` today (`api/mcp_app.py`), so the
engine has no knowledge that a protocol server exists. `gateway.py` is imported by `server.py` and by
every future embedder path, so anything *it* imports spreads with it. Putting a FastMCP-shaped
function there would make the MCP framework a dependency of the engine — and
[architecture § Embedding surface](../../architecture.md#embedding-surface) promises a host application
can use Meteoscape *"without starting MCP, HTTP, or any other server."* An embedder who never runs a
protocol server would pull one in anyway. Fact 8 is the symptom; this is the cause.

Nor does a surface-agnostic wrapper rescue it: FastMCP passes the server positionally, so a
"generic" helper would need `*_: object` in its signature purely to swallow that argument — leaving
it FastMCP-shaped anyway, only implicitly, and wrapping two lines to do it.

When [0165](../../tickets/01-0165-rest-surface.md) lands it writes the same two lines against its own
hook; if a third surface ever arrives, the thing to extract is *surface lifespan wiring*, which
belongs in `api/` and not next to the protocol.

No `on_shutdown` parameter and no catch. Two reasons, both narrowing:

- **Propagation satisfies the criterion.** *"Reported and does not propagate as a request-path
  error"* — `aclose()` is not the request path, and a traceback naming what failed to release as the
  process exits is a report. The client has already disconnected; the consequence is nil.
- **One surface is not a pattern.** [0165](../../tickets/01-0165-rest-surface.md) will register its own
  lifespan over the same hook (fact 3). If a third surface arrives, factor then — not from one shape.

`server.py` therefore does not change beyond assembling the list.

## Rejected at the align — recorded so they are not re-proposed

- **A process-wide keyed client cache.** Not merely leaky — *incorrect*. A process outlives event
  loops, and MongoDB's "one client per application" means one per **loop**, a scope shorter than the
  process.
- **Host-supplied resources** (`compose(..., mongo_client=...)`). Cannot reach Weaver-allocated
  stores, and would make `pymongo` a public dependency of the embedding surface.
- **A third `Manifold` verb** (`close` / `free` / `collapse`). Of the nine roadmap items needing
  winding down, only four are Manifolds; the ledger, observability, the REST surface and a future
  accumulator are not, so it buys two mechanisms where one does. `Closeable` is the third instance of
  the `Countable` / `Writable` facet pattern instead.
- **A separate composition handle.** `Gateway` is permanently 1:1 with its graph, and the surface
  that must *perform* teardown is the one already holding it.
- **`__aenter__` / `__aexit__`.** `contextlib.aclosing` supplies the with-form from stdlib.
- **Per-allocator release.** A schedule-driven accumulator ([#44](../../concerns.md#44-dedicated-live-archive-store-for-throughput))
  belongs to neither allocator.

## Stages

Every stage lands green; nothing here needs a red interval.

**1 — relocate, then add the facet and the release.** Move `api/gateway.py` → `gateway.py` and its
test up to `tests/deterministic/test_gateway.py`, updating the 5 imports and `api/__init__.py`'s
docstring, which stops applying caller policy once the boundary leaves (fact 1) — a pure move, no
behaviour, green before anything is added. Then add `Closeable` and the private collector to it, and
give `Gateway` the construction-site varargs and `aclose()`. Additive from there (fact 4).

Keeping the move as its own commit matters: a rename mixed with new behaviour is a diff nobody can
read, and if the relocation is ever reverted the facet should not have to move with it.

**Neither name is exported from `src/meteoscape/__init__.py`**, which re-exports only `SourceKey` and
`main`. The embedding Edge record states the rule this obeys — *"no internal type becomes public
merely because it might participate in an eventual facade"* — and 0125 selects what becomes public.
Called out because a lifecycle primitive is exactly the sort of thing that gets exported by reflex.

*Proves:* a composition holding nothing closes without error · two fakes release in **LIFO** order,
asserted by a shared recorder, not by two independent flags · a second `aclose()` releases nothing a
second time · **one that raises does not prevent the next from being released**, and the raised
`ExceptionGroup` contains its exception · a stateless object without `aclose` is simply not
`Closeable`.

*Also proves:* a construction site that mostly holds nothing is passed over member by member, and
the survivors keep their order across groups — since LIFO release is only meaningful against a known
order, and a real site is mostly inert.

**2 — compose collects.** `StoreFactory` remembers what it creates, `SourceRegistry` answers for its
providers, and `compose` hands both to the `Gateway`. `Weaver` untouched.

*Proves:* a fake `Closeable` provider wired through `compose` is released by `gateway.aclose()` — end
to end, since the provider catalogue is already a `compose` parameter · `StoreFactory.created` holds
what `create` returned · **no producer built from the shipped `CATALOG` satisfies `Closeable`**,
asserted over the catalogue itself rather than by reading `Gateway`'s private list, so the claim
"nothing shipped holds anything" is checked directly and will fail the day a shipped producer starts
holding without wiring release.

*Not proved here:* that a **store** holding a resource is released through `compose`. `compose`
builds its own `StoreFactory`, so a fake one can only arrive by rebinding the name or widening the
signature — and both buy a proof [0145](../../tickets/01-0145-persisting-store.md) gets for free, since
a real `SQLiteStore` reduces the test to *compose a profile declaring it, `aclose()`, assert the
connection closed*, with no fake anywhere. A fake factory would also have to re-implement the
recording it is meant to check, since overriding `create` is what skips it. Deferred deliberately —
see Limitations.

**3 — the server releases.** `build_mcp_app` registers the lifespan.

*Proves:* a recording gateway passed to `build_mcp_app` is released when an `async with Client(app)`
session **exits** — and, per fact 6's ordering requirement, not before: the same test asserts the
gateway is still unreleased *inside* the session, after a successful `call_tool`. That second
assertion is the one that matters; without it the test would pass equally if teardown fired at the
wrong time. Fact 6 makes this a real end-to-end proof over the idiom `test_mcp_app.py` already uses,
rather than an inspection of FastMCP internals.

**4 — layout note.** `module-layout.md` gains a top-level `gateway.py` entry (Gateway + the
`Closeable` facet) and loses `gateway` from the `api/` line, which becomes
`mcp_app` alone; the `compose` injection entry is updated; and `store.py`'s line is corrected —
`StoreFactory` is described there as *"Allocates `MemoryStore`s"*, which stops being the whole truth
once it also remembers them. The **dependency-rule line** gains `manifold ← gateway ← api`:
`gateway.py` imports the algebra and nothing else, `nodes/` never imports it (fact 8), and surfaces
import the composition rather than the reverse — so `gateway` and `nodes` are independent peers above
`manifold`, not a tier between them.

[`edge/embedding.md`](../../edge/embedding.md)'s **de-facto section** gains the release half of the
composition path — it ends at `Gateway.resolve(Selection) → Coverage`, and an embedder's de-facto
path now has a second verb. It names no module path, so the relocation needs nothing there.

This waits for implementation on purpose: an Edge record states living status, so it must not
describe an `aclose()` that does not yet exist. The record's *Open* and *Roadmap* entries were
already corrected at the align, since those describe decisions rather than code. Docs only.

## Standing constraints

Not limitations to accept but invariants the design now depends on; each would be a silent failure,
so each is stated here rather than discovered later.

- **Every provider must be constructed through the binder.** The collection reads
  `SourceRegistry`, not the woven graph — which is exactly why it works, since a provider wrapped in
  a `Reservoir` is still `registry[key].provider`. A provider built anywhere else is invisible to
  teardown. The one path where this could break is `ProviderManifest.expand`, currently unbuilt
  (`raise NotImplementedError("OfferingDef expand (name=None) is not built yet")`); whoever builds it
  must register each expanded provider, and this RFC is the reason.
- **`StoreFactory` becomes stateful.** It holds references to every store it created for the
  composition's life. Nothing new is retained — the graph already holds them — but it is no longer a
  pure factory, and a subclass overriding `create` without calling `super()` collects nothing. True
  of the existing test doubles and harmless there; it would not be harmless in a production
  substrate subclass — which is [0145](../../tickets/01-0145-persisting-store.md)'s to meet, since it
  brings the second substrate and owns the extension shape.
- **Teardown is attempted once.** Emptying the list is what delivers the ticket's idempotence, and it
  has to be *our* list: `Closeable` is structural, so nothing's own `aclose()` can be required to
  tolerate a second call. Emptying it before releasing rather than after makes that unconditional —
  a second call after a failure, after cancellation, or from another task releases nothing and raises
  nothing, with no lock, since the swap completes before the first `await`. Cancellation therefore
  strands whatever had not yet been released: `CancelledError` is a `BaseException`, so it propagates
  instead of joining the group, which is deliberate — catching it to keep going would swallow
  cancellation. The shipped server never meets that, since FastMCP shields lifespan teardown
  (fact 3); an embedder cancelling its own shutdown can.

## Limitations and follow-ups

- **Use-after-close is undefined.** `aclose()` releases but leaves `best_view` in place, so a
  `resolve()` afterwards still runs and fails *through the released resource* — `AsyncMongoClient` documents
  that a closed client raises `InvalidOperation`, which the Probe would surface as a
  `RuntimeFailure`, i.e. as though the upstream were at fault. No distinct "this composition is
  closed" category exists. Not built here: it needs no mechanism for the shipped server, which closes
  once on the way out, and inventing a category before the public failure model is settled is exactly
  what [#39](../../concerns.md#39-python-embedding-surface-and-public-failures) owns — it already
  inventories `runtime-failure` carrying faults that are not a producer's. Recorded so 0125 meets it
  as a known question rather than a surprise. The MCP surface has one concrete instance: because the
  lifespan is ref-counted (fact 3), a **second** `Client(app)` session against the same app re-enters
  it and runs against the composition the first session's exit already released. No shipped path does
  this — the stdio server has one session for the process, and each test builds its own app — but a
  host reusing an app across sessions would.
- **Calculators are not collected.** A `CalculatorManifest` supplies a plain `fn`, so no calculator
  holds anything today. A future stateful calculator plugin would need collecting at the same seam —
  belongs with [#26](../../concerns.md#26-provider--calculator-plugin-scaffolding), not here.
- **`runtime_checkable` checks method presence, not signature** — any object with an `aclose`
  attribute is `Closeable`. Accepted; the check runs once at build.
- **The seam is unexercised by a real `Closeable` until [0124](../../tickets/01-0124-mongo-obs-source.md).**
  That is the point of building it first, but it means 0124's align should confirm the seam fits
  before its implementation rather than assuming it.
- **A store's release is proven at [0145](../../tickets/01-0145-persisting-store.md), not here.** Every
  store the Weaver allocates is recorded, and `Gateway` releases what it is handed — but that a
  *store* holding a resource survives the whole path is checked where a real one exists and the test
  needs no fake. Until then the store half of `compose`'s collection is read, not run: dropping
  `stores.created` from the argument list would break no test, and 0145 is where that would surface.
- **`compose` does not take the `StoreFactory`.** Passing one in would make the store half testable
  now and may well be where store selection lands, but 0145 reserves the decision in as many words —
  *"No configuration, factory, registry, or public extension shape is selected ahead of this ticket's
  align"* — and building the factory inside is what makes one clock **structural** rather than
  conventional, which both [`module-layout.md`](../../module-layout.md) and
  [`edge/embedding.md`](../../edge/embedding.md) record as the reason it is built there. A shape chosen
  against one substrate to serve one test is chosen for the wrong reason.
- **`HttpxTransport` stays per-call** — [ticket Out of scope](../../tickets/done/01-0116-composition-lifetime.md),
  with its trigger.
- **The `TODO` in `aclose()`** must name
  [02-0195](../../tickets/02-0195-minimal-resolution-logging.md): teardown failures surface only as the
  group, because the logging boundary and sensitive-field policy are that ticket's, and a message
  must never carry a connection string. The
  [doc-corpus gate](../../tickets/done/01-0127-docs-integrity-gate.md) verifies the pointer resolves.
- **The `Gateway` *name*** — still open at
  [#39](../../concerns.md#39-python-embedding-surface-and-public-failures), and now the only part of
  that question left, since this ticket answers the placement half. A caller-policy boundary that
  also owns the composition's shutdown is arguably misnamed; 0125 decides, because 0125 publishes it.

## Footprint

~52 lines in `src` (gateway 35 — of which 15 are the facet and collector — store 5, server 7,
mcp_app 5) plus a pure file move, and ~110 in tests — well inside the ticket-size budget, so no
decomposition is needed.
