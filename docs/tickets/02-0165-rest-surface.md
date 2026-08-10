# REST surface

- **Status:** Planned (own align and an Edge record precede) — minted at the 2026-08-10 beeline
  align.
- **Depends on:** [supported Python embedding surface](./01-0125-supported-python-embedding.md)
  (not mechanically — see below — but by decision: the public failure hierarchy and result contract
  are settled there first)
- **Outcome:** The deployment shape the operator actually runs — meteoscape reachable over HTTP,
  serving the same weather semantics as MCP and the embedding surface.

## Parent

Release 02 is contract-deferred (no requirements doc yet — [delivery status](./README.md)). This
ticket does **not** amend v1: [v1-requirements](../v1-requirements.md) defers HTTP transport by name
and that stays true for the v1 contract — REST arrives as release-02 surface work, after the v1
contract closes on stdio MCP plus the embedding surface. Durable context:
[roadmap Phase 2](../product-roadmap.md) ("optional REST surface if demand appears" — demand
appeared, 2026-08-10) and [architecture § Gateway](../architecture.md#gateway--caller-policy-boundary).

## What to build

A protocol edge over the **same seam MCP already uses**. `mcp_app` composes a `Selection` and calls
`Gateway.resolve`; the Gateway is explicitly *"the one surface-neutral policy seam"*, and *"surfaces
serialize the Coverage; they do not sample"*. So a REST edge is a sibling of the MCP edge, not a
layer over the embedding facade — **the engine does not move**.

```
        MCP (stdio)  ─┐
        REST (HTTP)  ─┼──►  Gateway  ──►  profile root  ──►  …
   embedding surface ─┘     (caller policy: authz, rate-limit, quota, or pass-through)
```

What REST drags in is everything *around* the engine, because unlike stdio MCP, an HTTP port is
reachable by someone other than its owner:

- **The Gateway's caller-policy seam stops being null.** Caller identity, authz, and rate-limiting
  become real for the first time — and this is where **caller** quota lives, the other meter from
  the [vendor-call ledger](./02-0124-vendor-call-ledger.md)'s. Two meters, two layers: what a caller
  spends against us here, what we spend against a vendor there.
- **A second serialization contract to keep equivalent** with MCP and the embedding surface — the
  same equivalence obligation [0125](./01-0125-supported-python-embedding.md) carries, now with a
  third party to it.
- **A long-running deployment shape** rather than a per-session process, which is part of why the
  [persisting store](./02-0145-persisting-store.md) sits just ahead of this in the queue.

## Decisions this ticket's align owns

- **The resource model** — one `forecast` endpoint mirroring `forecast_hourly`, or a resource
  shape that the MCP tool is a projection of.
- **Failure → status code.** [#39](../concerns.md#39-python-embedding-surface-and-public-failures)'s
  four classes (capability / composition / **unbuilt** / **invariant break**) have to render as
  status codes here, which is a sharper forcing function than a language API is. 0125's align
  settles the hierarchy first; this align may reopen the *mapping* and should expect to.
- **Caller policy shape** — what the Gateway's non-null policy actually is, and whether it ships
  with this ticket or immediately behind it.
- **Serialization format** — CoverageJSON and a `format` selector are named v1 non-goals; whether
  they arrive here or later is this align's.

## Acceptance criteria

- [ ] An HTTP request resolves the same weather product as the equivalent MCP call against the same
      configured profile: same served window, parameter membership, canonical values, provenance,
      nodata, and absence outcomes.
- [ ] The edge composes a `Selection` and calls `Gateway.resolve` — it does not sample, crop, or
      touch manifold internals; an import-direction guard pins it, as the Probe seam is pinned.
- [ ] Every public failure class renders as a documented status code, and an engine invariant break
      is never reported wearing a producer's fault.
- [ ] Caller policy is enforced at the Gateway, not in the edge — the same policy applies when the
      MCP surface is used.
- [ ] A [REST Edge record](../edge) exists, carrying Contract, Invariants (each marked guarded or
      **⚠ unguarded**), Concerns, and Roadmap.
- [ ] No secret or credential is observable through the surface, including in error bodies.

## Parent scope addressed

- Roadmap Phase 2 (operational substrate): optional REST surface; self-host packaging.
