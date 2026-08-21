# Composition lifetime and shutdown

- **Status:** Done (2026-08-21) — aligned 2026-08-20 jointly with the
  [Mongo obs source](../01-0124-mongo-obs-source.md)'s, implemented and reviewed the next day.
- **Type:** HITL
- **Kind:** Maintenance
- **Depends on:** [config and secrets](./01-0123-config-secrets-degrade.md) (a composition root
  declares the profile and supplies the secret a connection is built from)
- **Blocks:** [Mongo obs source](../01-0124-mongo-obs-source.md) (the first producer that must hold a
  connection between requests), [supported Python embedding
  surface](../01-0125-supported-python-embedding.md) (which publishes construction and teardown as
  API, so the shape must be chosen, not inherited)
- **Outcome:** A composed graph can be shut down, and a producer holding a long-lived resource
  releases it on that shutdown; the server and any embedder use the same one way to do it.

## Parent

Carved out of the [Mongo obs source](../01-0124-mongo-obs-source.md), which names the non-HTTP
transport as its own first. That ticket keeps the source and its schema mapping; this keeps the seam
the source rides, so the seam is decided at an align rather than invented inside an implementation.
*Position note: 0123 and 0124 are adjacent and 0122 is spent, so this takes the nearest free slot
before its origin; the row sits where the work happens.*

## What goes wrong today

Nothing in `src` owns a resource that outlives a single call. Every connection the code makes is
opened and closed inside one `fetch`:

```python
# nodes/providers/base.py — HttpxTransport.fetch()
async def fetch(self, request):
    async with httpx.AsyncClient(...) as client:   # opened per call
        response = await client.get(...)
        return response.json()                     # closed per call
```

So `compose()` can hand back a `Gateway` and walk away — there is nothing to release:

```
today:   gateway = compose(profile, catalogs, secrets, clock)
         # ...and that is the whole lifecycle. No close, no context manager.
```

`grep` for `aclose`, `async def close`, or `__aenter__` across `src` returns nothing.

A Mongo client cannot work that way. It is a connection pool: built once, held for the life of the
process, closed at the end. Opening one per request pays a TCP handshake and an auth round-trip on
every call, and never reuses a pooled socket. The obs source therefore needs somewhere to **hold** a
client between requests and somewhere to **release** it when the caller is done.

**Why this is not the obs source's private detail.** The
[embedding surface](../01-0125-supported-python-embedding.md)'s whole deliverable is publishing
construction and teardown to embedders as supported API. If the seam is invented as a private detail
one ticket earlier, 0125 inherits a shape nobody chose. That is the shape
[0123](./01-0123-config-secrets-degrade.md) found in the `.env` decision — structured
configuration went through an env namespace because env was what already existed, and the cost
surfaced as implementation detail instead of as a design question.

## What to build

One way to release what a composed profile opened, reaching every producer that holds something,
used identically by the shipped server and by an embedder.

- **A producer that holds nothing stays unchanged.** Today that is every producer; the seam must not
  make `HttpxTransport` or the calculators carry a teardown they do not need.
- **Shutdown is total and idempotent.** Composition builds a graph; releasing it releases everything
  in it, and doing so twice is not an error — an embedder in a test fixture will.
- **The server uses it.** `main()` is the first caller; it does not get to leak because it is
  short-lived.
- **A failure to release is not a request failure.** Teardown runs when the caller is already done,
  so it reports rather than raises into the product path.

## Decisions this ticket's align owns

Resolved at the 2026-08-20 align, run jointly with the
[Mongo obs source](../01-0124-mongo-obs-source.md)'s. The rejected alternatives and the evidence that
killed each one belong in this ticket's `/plan-impl` RFC; what survives here is the decision and its
reason.

- ~~**Explicit `aclose()` or async context manager** — or both, one wrapping the other.~~
  **One `aclose()`; no `__aenter__`.** `contextlib.aclosing` already turns any object exposing
  `aclose()` into an async context manager, so shipping our own would re-implement stdlib inside the
  published surface — and a `with` block whose body is an entire application is the shape ASGI
  lifespan exists to avoid. Adding `__aenter__` later is additive; removing it from a published API
  is not. Half of this was never a choice: `AsyncMongoClient.close()` is a coroutine, so a sync
  close is unrepresentable.
- ~~**What the caller holds** — whether shutdown hangs off the `Gateway` or off a separate
  composition handle.~~ **The `Gateway` itself. No new type, and `compose()`'s signature is
  unchanged.** A Gateway stands in permanent 1:1 relation to the graph it fronts, and the surface
  that must *perform* teardown — FastMCP's `lifespan`, inside the MCP app — is the one already
  holding it, so a separate handle would force `build_mcp_app` to take both. Every closeable lives
  under `best_view`, the subtree the Gateway already owns. **It also leaves `api/`**: a type every
  surface *receives* is not a surface-layer type, and the move costs five import lines against a
  rename's corpus-wide sweep — the two were bundled and mispriced together at first. `Closeable` and
  its collector live with it rather than in a leaf of their own. Whether `Gateway` remains the right
  *name* stays with [#39](../../concerns.md#39-python-embedding-surface-and-public-failures), which
  publishes it.
- ~~**How a producer advertises that it holds something.**~~ **A `Closeable` facet Protocol the
  Weaver collects** — the third instance of the `Countable` / `Writable` pattern, not a widened
  `Manifold`. Of the nine things on the roadmap that need winding down, only four are Manifolds
  (both Mongo sources, `SQLiteStore`, the bulk store); the ledger, observability, the REST surface
  and a future accumulator are not, so a `Manifold` verb would buy *two* mechanisms where one does.
  Lifetime is operational infrastructure, not algebra. A producer holding nothing implements
  nothing.
- ~~**Whether construction becomes async.**~~ **Dissolved — it does not have to.** The
  `AsyncMongoClient` constructor is documented non-blocking and takes no loop; the eager path is a
  separate opt-in `await client.aconnect()`. `compose()` stays sync and no call site moves for this
  reason. *Consequence belonging to 0124, not here*: a connection string that is present but wrong
  then fails at first request rather than at boot, which sits oddly beside 0123's
  key-absent-refuses posture.
- ~~**Whether `HttpxTransport` moves to a held client** as a consequence.~~ **No — moved to Out of
  scope with a trigger.** The seam lands first, so converting it afterwards is strictly cheaper than
  doing it now; it is the only behaviour change to a working path in an otherwise additive ticket,
  and no measured latency customer exists.

Settled during the align rather than listed above:

- **One release path, not two.** Per-allocator release (`StoreFactory` frees what it created,
  `SourceBinder` what it instantiated) would need a third path the day a schedule-driven accumulator
  ([#44](../../concerns.md#44-dedicated-live-archive-store-for-throughput)) lands, since it belongs to
  neither.
- **`compose` names the construction sites** — the two it already holds, handed whole to the
  `Gateway`, which decides which of their members hold anything. `weave` keeps returning a
  `Manifold` and keeps stepping out; nothing is threaded through it.
- **Release is LIFO; idempotence is by clearing the list**, not by a flag.
- **A failed release does not strand the rest.** Every `Closeable` is attempted, failures are collected,
  and `aclose()` raises an `ExceptionGroup`. That does not violate the criterion below, because
  `aclose()` is not the request path. No log line: the logging boundary and the sensitive-field
  policy belong to [02-0195](../02-0195-minimal-resolution-logging.md), and a teardown message must
  never carry a connection string — the code carries a `TODO` pointing there.
- **The driver was not a choice.** Motor reached end of life 2026-05-14, leaving `AsyncMongoClient`.
  Release is *required* rather than merely tidy because it binds to one event loop: MongoDB's "one
  client per application" means one per **loop**, a scope shorter than the process — which is why a
  process-wide keyed client cache is incorrect here, not just untidy.

## Acceptance criteria

- [x] A composed graph can be shut down through one documented call, and calling it twice is not an
      error. — `Gateway.aclose()`, proven by `test_second_aclose_releases_nothing_again` and
      `test_composition_holding_nothing_closes`.
- [x] A producer holding a long-lived resource releases it on that shutdown — pinned by a fake
      producer that records release, not by inspecting the shutdown path. —
      `test_compose_releases_a_provider_that_holds_a_resource`, end to end through `compose` with
      `fakes.CloseableProvider`.
- [x] Every existing producer composes and serves unchanged, with no teardown implemented for
      producers that hold nothing. — the suite is green at 433, and
      `test_no_shipped_producer_holds_a_resource` asks the shipped catalogue directly, with a
      length check so it cannot pass vacuously.
- [x] The shipped server releases what it composed when it stops. —
      `test_the_server_releases_its_composition_when_the_session_ends`, which also asserts release
      has *not* happened mid-session, so the ordering is proven rather than only the outcome.
- [x] A teardown failure is reported and does not propagate as a request-path error. —
      `test_one_failed_release_does_not_strand_the_rest`: the sibling is still released, and the
      `ExceptionGroup` carries the failure.
- [x] The align's resolutions are recorded in their durable homes before implementation starts —
      including whichever of `architecture.md` or an ADR owns the seam. — architecture § Gateway and
      its Contract-surfaces row, the `Closeable` glossary entry, `module-layout.md`, and
      [#39](../../concerns.md#39-python-embedding-surface-and-public-failures). No ADR was minted: the
      seam is a contract sentence, and the reasoning behind it lives in the RFC.

**Not covered, deliberately:** that a *store* holding a resource is released through `compose` —
deferred to [0145](../01-0145-persisting-store.md), where a real `SQLiteStore` makes the test natural
and needs no fake factory. Until then that half of the collection is read but not run.

## Out of scope

- **The Mongo client itself**, its schema mapping, and its capability —
  [Mongo obs source](../01-0124-mongo-obs-source.md).
- **The public embedding contract** that publishes this seam to embedders —
  [supported Python embedding surface](../01-0125-supported-python-embedding.md).
- **Store persistence lifetime** — a persisting `Store` will hold a connection too, but its own
  substrate questions are [persisting SQLite Store](../01-0145-persisting-store.md)'s. This seam
  should fit it; proving that is 0145's.
- **Moving `HttpxTransport` to a held client.** Every vendor call still builds and destroys its own
  `httpx.AsyncClient`, so there is no keep-alive and no TLS session reuse. Converting it rides the
  seam this ticket builds, which is exactly why it waits: afterwards it is a small change against an
  established seam, and it is otherwise the only behaviour change to a working, parity-tested path.
  **Trigger:** measured vendor-call latency, or a second HTTP-shaped transport arriving.
- **Request-path cancellation and timeouts** — a different lifetime question, not this one.
