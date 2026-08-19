# Supported Python embedding surface

- **Status:** Planned — its own embedding-edge align precedes implementation; this ticket assigns
  the Phase-1 delivery without preselecting the facade.
- **Depends on:** [Mongo obs source](./01-0124-mongo-obs-source.md) (the first non-HTTP,
  past-facing source supplies lifecycle and construction evidence)
- **Outcome:** A documented, supported Python package boundary resolves the same available forecast
  product as MCP without starting a protocol server, with expected failures exposed through public
  API.

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

Embedding is the pilot deployment's first consumption shape. It ships under **live equivalence**:
the embedding and MCP surfaces expose the same weather behavior available when this ticket lands,
and both widen as later capabilities land. The [REST surface](./01-0165-rest-surface.md) is a sibling
over the `Gateway` seam, sequenced later so this ticket settles the public failure hierarchy first;
REST may render those failures differently over HTTP.

Then ship that contract end to end. An embedding host resolves the woven best-view profile without
constructing or running FastMCP; the MCP and embedding surfaces expose equivalent weather semantics
for equivalent requests, without requiring identical representations or shared adapter code.

## Acceptance criteria

- [ ] A documented, supported package import resolves the profile's available hourly forecast product
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

## Parent scope addressed

- User story 16
- User story 17
- Acceptance criterion 10
- Acceptance criterion 11
