# Edge — Embedding surface

- **Status:** Stub

The seam record for the supported Python embedding surface. Most of this edge is deliberately
unresolved — the facade decisions live at
[concern #39](../concerns.md#39-python-embedding-surface-and-public-failures), and this record
aggregates what is decided, what exists de facto, and what remains open. It does not force any
open decision.

## Contract

**Decided** (resolved at #39, [architecture §Embedding surface](../architecture.md#embedding-surface)):

- Meteoscape is a **supported headless Python library from Phase 1** — an embedding application
  uses its weather capabilities without starting MCP, HTTP, or any other server. A first-class
  product surface, not documentation for internal imports.
- **No internal type becomes public merely because it might participate** in an eventual
  facade — the public surface is selected deliberately, not accreted.

**De facto today — explicitly *not* promised:**

- The package root exports only `SourceKey` and `main`.
- The only usable composition path is `server.compose(profile, providers, calculators, secrets,
  clock, stores) → Gateway`, requiring `ProfileConfig`, both plugin catalogues, a secrets map, a
  `Clock`, and a `StoreFactory`; requests then run `Gateway.resolve(Selection) → Coverage`.
  Every name in that sentence is an internal type an embedder must import from internal modules.

**Open** (all at #39): the smallest stable facade and lifecycle; whether construction is
directly exposed; how shipped and third-party manifests are supplied; whether `Gateway`,
`Selection`, `Coverage`, or higher-level alternatives become public; what boundary is shared
with server adapters; Selection-composition ergonomics (mode builders over hand-assembled axes —
[architecture §Request modes](../architecture.md#request-modes)).

## Invariants

None promisable yet — the record is a Stub because the contract is unselected, not because the
work is unstarted. Candidate promises waiting on #39's decisions:

- Request-path failures inherit `MeteoscapeError`; build-time misconfiguration stops the boot as
  `CompositionError` and never reaches a request path — **⚠ unguarded** (true of today's code
  shape, but #39 explicitly leaves the public exception hierarchy open: `CompositionError` sits
  outside `MeteoscapeError`, settings validation escapes separately, and invariant bugs escape
  as ordinary exceptions by design).
- Observable consistency between embedded and protocol use of the same profile —
  **⚠ unguarded** (named at #39 as an open compatibility question, no defined check).

## Concerns

- [#39 — Python embedding surface and public failures](../concerns.md#39-python-embedding-surface-and-public-failures)
  — the owner of this edge's open Contract: facade shape, public failures, `0.x` compatibility.
- [#40 — Composing servable requests at the embedding edge](../concerns.md#40-composing-servable-requests-at-the-embedding-edge)
  — the embedder composes a `Selection` by hand and learns it was unservable only from a
  `CapabilityMismatch` after the fact. Owns the inventory of which mismatch cases this edge can
  dissolve (shape errors, totally — the `SelectionDomain` builder case; coverage misses, only
  advisorily; races, never) and what a composition helper may honestly promise given that
  `Capability` is not a perfectly faithful self-description. Its Arm-1 table is kept current as
  raise sites land.
- [#23 — Spatial vs temporal `RegularAxis` types](../concerns.md#23-spatial-vs-temporal-regularaxis-types)
  — if the axis split lands, it must stay **invisible at this surface**: one axis name per kind,
  or absorbed by facade builders (the m4 align priced sibling public types as an
  embedding-vocabulary cost and deferred them).
- [#12 — Curvilinear domains](../concerns.md#12-curvilinear-domains) — a future non-separable
  request composition arrives as a sibling representation in the embedder's request vocabulary;
  the interface promise is that today's shapes survive it.
- [#26 — Provider / calculator plugin scaffolding](../concerns.md#26-provider--calculator-plugin-scaffolding)
  — how an embedding host supplies third-party manifests is part of this edge's construction
  story.
- [#35 — Calculator satisfiability vs optional-provider degrade](../concerns.md#35-calculator-satisfiability-vs-optional-provider-degrade)
  — the embedder's configuration experience when optional providers are absent: what composes,
  what degrades, what refuses to boot.

## Roadmap

Tentative — stages below #39's resolution have no owning tickets yet; they are the expected
shape of the work, not commitments.

1. Facade and lifecycle selected; delivery minted as a Phase-1 ticket — decision at
   [#39](../concerns.md#39-python-embedding-surface-and-public-failures).
2. Public failure contract — exception hierarchy, phase boundaries, actionable context — #39.
3. Request-composition ergonomics — `SelectionDomain` / mode builders ride
   [m4](../tickets/done/01-0100-snapped-t-request-mode.md) and
   [003c](../tickets/done/01-0110-request-shaping.md); they become embedder vocabulary when the facade
   lands. Whether those builders are merely **shape-safe** (unservable shapes unrepresentable, no
   capability read) or **capability-aware** (validated against a live `Capability`, therefore
   advisory) is [#40](../concerns.md#40-composing-servable-requests-at-the-embedding-edge).
4. `0.x` compatibility policy — supported import paths, deprecation mechanics, embedded ↔
   protocol consistency — #39.
5. Third-party plugin authoring — how an embedding host *supplies* manifests
   ([#26](../concerns.md#26-provider--calculator-plugin-scaffolding)); how a Provider is *authored* is
   its own edge, [edge/provider.md](./provider.md).
