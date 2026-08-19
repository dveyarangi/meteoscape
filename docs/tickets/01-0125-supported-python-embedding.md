# Supported Python embedding surface

- **Status:** Planned — its own embedding-edge align precedes implementation; this ticket assigns
  the Phase-1 delivery without preselecting the facade.
- **Reaffirmed 2026-08-10 (beeline align):** embedding is the deployment's **first** consumption
  shape; the [REST surface](./01-0165-rest-surface.md) follows later in the beeline rather than
  replacing it. The two are siblings over the same `Gateway` seam, not a stack — an edge needs no
  public facade, as the MCP edge already demonstrates — so REST does not depend on this ticket
  mechanically. It is sequenced after it by decision, so the public failure hierarchy
  ([#39](../concerns.md#39-python-embedding-surface-and-public-failures)) is settled here first;
  expect REST's status-code mapping to reopen the *rendering* of those classes, which is normal.
- **Moved up 2026-08-08 (align):** the first real embedder arrives with the local-station work (the
  operator's application embeds meteoscape rather than running the MCP server), so this surface no
  no longer waits for the former v1 tail. Consequence: the equivalence rule changes from "MCP-equivalent **v1**
  semantics" (ship only when everything exposed is done) to **"equivalent to whatever is live"** —
  the facade ships early and its capability grows as tickets land, exactly as the MCP surface already
  does. The former dependency chain (off-grid homogenization, per-parameter selection, config,
  errors) is thereby dissolved as a *gate*; those tickets now merely widen what both surfaces serve.
  The ticket's own align (#39/#40) still precedes implementation.
- **Outcome:** A documented, supported Python package boundary resolves the same v1 forecast product
  as MCP without starting a protocol server, with expected failures exposed through public API.

## Parent

[`docs/v1-requirements.md`](../v1-requirements.md) — embedder user stories 16–17 and acceptance
criteria 10–11.

## What to build

Turn the [Embedding Edge record](../edge/embedding.md) from a Stub into the supported Phase-1 Python
surface. The ticket's opening align settles the decisions still owned by
[#39](../concerns.md#39-python-embedding-surface-and-public-failures) and
[#40](../concerns.md#40-composing-servable-requests-at-the-embedding-edge): the smallest stable facade
and lifecycle, construction and shipped-manifest experience, request-composition ergonomics, public
result and failure types, embedded ↔ protocol compatibility, and the `0.x` compatibility policy.
The failure half opens from #39's **class inventory** (2026-08-09): *capability*, *composition*,
*unbuilt*, and *invariant break* are four different things sharing two wire categories — an engine
invariant break must not reach a product surface wearing a producer's fault. The leak sites carry
`TODO(#39)` markers in `sampling.py`, `gateway.py`, `arbiter.py`, and `errors.py`.
No existing internal type becomes public merely because it participates in today's composition path.

Then ship that contract end to end. An embedding host resolves the woven best-view profile without
constructing or running FastMCP; the MCP and embedding surfaces expose equivalent weather semantics
for equivalent requests, without requiring identical representations or shared adapter code.

## Acceptance criteria

- [ ] A documented, supported package import resolves the complete v1 hourly forecast product
      headlessly, without constructing or starting an MCP, HTTP, or other protocol server.
- [ ] Equivalent embedded and MCP requests against the same configured profile produce equivalent
      served windows, parameter membership, canonical values, provenance, nodata, and absence
      outcomes; integration tests exercise both surfaces.
- [ ] Expected construction/configuration and request failures are exposed through a documented
      public contract; callers do not import internal exception types to handle them.
- [ ] Supported import paths and the `0.x` compatibility/deprecation policy are documented and
      guarded by packaging and integration tests.
- [ ] The [Embedding Edge record](../edge/embedding.md) carries the shipped Contract and per-invariant
      validators; it no longer relies on de-facto internal imports.

## Blocked by

Nothing. This section previously listed off-grid homogenization, per-parameter selection, config,
and errors — the v1-tail gates that the 2026-08-08 align **dissolved** when it adopted the
live-equivalence rule (see the header). The list survived the align as stale text and is removed
here (2026-08-10). Those tickets now merely *widen* what both surfaces serve; none gates this one.

In queue order the surface still lands after
[008 — config and secrets](./done/01-0123-config-secrets-degrade.md), which is ordering, not
blocking.

The Coverage-contract point-exactness invariant (off-grid X/Y reported at the request, values from
the enclosing store cell) is already true and guarded by
[007](./done/01-0117-off-grid-homogenization.md); this surface inherits it as an observable promise
and its align does not re-decide it.

## Parent scope addressed

- User story 16
- User story 17
- Acceptance criterion 10
- Acceptance criterion 11
