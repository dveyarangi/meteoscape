# Supported Python embedding surface

- **Status:** Planned — its own embedding-edge align precedes implementation; this ticket assigns
  the Phase-1 delivery without preselecting the facade.
- **Moved up 2026-08-08 (align):** the first real embedder arrives with the release-02 work (the
  operator's application embeds meteoscape rather than running the MCP server), so this surface no
  longer waits for the v1 tail. Consequence: the equivalence rule changes from "MCP-equivalent **v1**
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

- [Off-grid homogenization](./01-0117-off-grid-homogenization.md) — completes the storing
  `Reservoir`'s exact-request-point behavior.
- [Per-parameter selection](./01-0170-per-parameter-selection.md) — completes multi-provider product
  membership and provenance semantics.
- [Config, secrets, and graceful degradation](./01-0180-config-secrets-degrade.md) — completes the
  construction behavior the embedding surface must expose.
- [Errors and partial success](./01-0190-error-taxonomy-partial-success.md) — completes the failure
  behavior the public contract must classify.

## Parent scope addressed

- User story 16
- User story 17
- Acceptance criterion 10
- Acceptance criterion 11
