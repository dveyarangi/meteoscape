# Composition lifetime and shutdown

- **Status:** Ready (align rides the Mongo obs source's)
- **Type:** HITL
- **Kind:** Maintenance
- **Depends on:** [config and secrets](./done/01-0123-config-secrets-degrade.md) (a composition root
  declares the profile and supplies the secret a connection is built from)
- **Blocks:** [Mongo obs source](./01-0124-mongo-obs-source.md) (the first producer that must hold a
  connection between requests), [supported Python embedding
  surface](./01-0125-supported-python-embedding.md) (which publishes construction and teardown as
  API, so the shape must be chosen, not inherited)
- **Outcome:** A composed graph can be shut down, and a producer holding a long-lived resource
  releases it on that shutdown; the server and any embedder use the same one way to do it.

## Parent

Carved out of the [Mongo obs source](./01-0124-mongo-obs-source.md), which names the non-HTTP
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
[embedding surface](./01-0125-supported-python-embedding.md)'s whole deliverable is publishing
construction and teardown to embedders as supported API. If the seam is invented as a private detail
one ticket earlier, 0125 inherits a shape nobody chose. That is the shape
[0123](./done/01-0123-config-secrets-degrade.md) found in the `.env` decision — structured
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

- **Explicit `aclose()` or async context manager** — or both, one wrapping the other. The choice is
  visible in 0125's published API, which is why it is not an implementation preference.
- **What the caller holds.** Today `compose()` returns a `Gateway`, which is a request-path object;
  whether shutdown hangs off it or off a separate composition handle decides whether the request
  path can see teardown at all.
- **How a producer advertises that it holds something.** An optional protocol the Weaver collects, a
  base-class no-op, or a registry the binder fills — this is the part that must not force every
  stateless producer to implement teardown.
- **Whether construction becomes async.** A pooled client can be built lazily on first use or eagerly
  at compose; eager construction makes `compose` async and changes every caller, so the trade is
  real and belongs to the align, not to the Mongo ticket.
- **Whether `HttpxTransport` moves to a held client** as a consequence. Per-call clients are a real
  cost once a second transport exists, but changing it is a behaviour change to a working path and
  may belong to its own ticket.

## Acceptance criteria

- [ ] A composed graph can be shut down through one documented call, and calling it twice is not an
      error.
- [ ] A producer holding a long-lived resource releases it on that shutdown — pinned by a fake
      producer that records release, not by inspecting the shutdown path.
- [ ] Every existing producer composes and serves unchanged, with no teardown implemented for
      producers that hold nothing.
- [ ] The shipped server releases what it composed when it stops.
- [ ] A teardown failure is reported and does not propagate as a request-path error.
- [ ] The align's resolutions are recorded in their durable homes before implementation starts —
      including whichever of `architecture.md` or an ADR owns the seam.

## Out of scope

- **The Mongo client itself**, its schema mapping, and its capability —
  [Mongo obs source](./01-0124-mongo-obs-source.md).
- **The public embedding contract** that publishes this seam to embedders —
  [supported Python embedding surface](./01-0125-supported-python-embedding.md).
- **Store persistence lifetime** — a persisting `Store` will hold a connection too, but its own
  substrate questions are [persisting SQLite Store](./01-0145-persisting-store.md)'s. This seam
  should fit it; proving that is 0145's.
- **Request-path cancellation and timeouts** — a different lifetime question, not this one.
