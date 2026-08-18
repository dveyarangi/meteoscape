# Session 0024 · 2026-08-08 · Purpose reframed, release 02 opened, TWC reverted

One arc from an honest question to a restructured queue. An overengineering assessment against the
codebase (docs ≈ 15.7k lines vs ~4.1k src / ~6.1k tests; every load-bearing abstraction carrying
exactly one concrete caller shape) led to reframing the project's purpose and its guarded risk —
not overengineering but **single-instance abstraction lock-in** — and to a sequencing strategy of
pulling differently-shaped concretes forward. An `/align` then walked seven branches: provider
identity, release structure, queue order, the operator's Collector database, archive-work
decomposition, division of labor, and the purpose statement itself. Three release-02 tickets were
minted at the end; a repo-wide sweep renamed two tickets and touched ~20 docs.

## Settled (one line each; the reference is the durable home)

- **Purpose and sequencing authority written in**: experience-synthesis framework; phases are a
  menu; the shape-diversity rule owns sequencing →
  [product-roadmap §Purpose and sequencing authority](../../../product-roadmap.md#purpose-and-sequencing-authority).
- **TWC reverted as v1's second provider** — the 2026-08-02 swap's premise (unverified access)
  dissolved; the code had never left TWC → [ticket](../../../tickets/done/01-0120-twc-provider.md)
  (identity-history note), [v1-requirements §Providers](../../../v1-requirements.md).
- **Release 02 opened, contract-deferred; a release is a contract-closure milestone, not a
  chronological gate** → [delivery README §Ticket numbering](../../../tickets/README.md#ticket-numbering).
- **Positions are one global line across releases** (folder sorts within a release; the delivery
  map is the cross-release order) → [delivery README §Ticket numbering](../../../tickets/README.md#ticket-numbering).
- **Embedding moved up (`0192 → 0125`) under the live-equivalence rule** — the v1-tail gate
  dissolved; capability grows as tickets land →
  [ticket](../../../tickets/01-0125-supported-python-embedding.md).
- **Queue re-staged**: store slices → off-grid homogenization → TWC → embedding → Mongo obs source
  → forecast-run archive source → correction calculator → v1 tail → plugin seam / grid file / FTP
  → [delivery README §Recommended execution order](../../../tickets/README.md#recommended-execution-order).
- **Archive work split by shape** (obs source ≠ run archive ≠ correction), three tickets minted
  decision-bearing → [02-0130](../../../tickets/02-0130-mongo-obs-source.md),
  [02-0134](../../../tickets/02-0134-forecast-run-archive-source.md),
  [02-0140](../../../tickets/02-0140-correction-calculator.md).
- **The Collector is the archive; meteoscape projects over it read-only** — its schema is an
  external contract → [#45](../../../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)
  (queued at mongo-obs-source), [glossary §Collector](../../../glossary.md).
- **A dedicated live archive Store is parked** (trigger: measured throughput pressure) →
  [#44](../../../concerns.md#44-dedicated-live-archive-store-for-throughput).
- **Division of labor**: the engine serves data products; the embedder owns decisions,
  presentation, and deployment-specific source integrations (plug-ins via
  [#26](../../../concerns.md#26-provider--calculator-plugin-scaffolding), never in-tree); bias statistics
  start operator-side and eventually become a meteoscape product →
  [product-roadmap §Priority candidate after v1](../../../product-roadmap.md#priority-candidate-after-v1-local-station-validation-and-bias-correction).
- **The forecast-history lead-time question is answered**: the Collector has been accumulating
  multi-provider, issue-slot-keyed forecasts and observations continuously → same roadmap section.
- **Deployment identifiers stay out of the repo** — deployment-specific names (client, region,
  station network) appear nowhere in docs or code; integrations carrying them are embedder
  plug-ins → enforced by sweep this session; rule carried in
  [#45](../../../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)'s
  plug-in boundary and the roadmap's division-of-labor paragraph.

## Delivery state

The in-flight work is unchanged by all of this: the four store slices
(`0115.0010`–`0115.0040`, RFCs 0011–0014) remain the current stage, `0115.0010` the only Ready
slice. The three release-02 tickets are Planned, each with "own align precedes." Queue and statuses:
[delivery README](../../../tickets/README.md).

## Open questions (all owned elsewhere; none live only here)

- Embedding facade, lifecycle, public failures, `0.x` policy — its align now also serves the 02
  sources' construction experience → [#39](../../../concerns.md#39-python-embedding-surface-and-public-failures) /
  [#40](../../../concerns.md#40-composing-servable-requests-at-the-embedding-edge),
  [ticket](../../../tickets/01-0125-supported-python-embedding.md).
- Observation-source semantics (obs freshness, station-located geometry vs the off-grid path) and
  the #45 mitigations → [02-0130](../../../tickets/02-0130-mongo-obs-source.md) align.
- Run selection within latest-complete-run scope, and `expand` vs sibling manifests for the three
  archive origins → [02-0134](../../../tickets/02-0134-forecast-run-archive-source.md) align; cross-run
  combination stays [#9](../../../concerns.md#9-cross-run-combination).
- Pairing mechanics, bias-product shape, parity tolerance, and the stability criterion that later
  licenses correction → [02-0140](../../../tickets/02-0140-correction-calculator.md) align.
- Live parity under an operator-supplied commercial key (no secret in evidence; routing/enforcement)
  → [ticket 0120 acceptance](../../../tickets/done/01-0120-twc-provider.md),
  [#41](../../../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).

## Continuation

1. Unchanged next implementation action: **0115.0010 with RFC 0011** (Cursor session, then
   `/review-impl` per slice).
2. At 0120 pickup: verify TWC payload unit self-reporting honestly (acceptance criterion); decide
   the parity-key handling.
3. Release-02 requirements doc: deliberately deferred until the first shapes land — do not write it
   preemptively.
4. The roadmap's later-shape menu (local grid file as an ERA5 slice, FTP transport, plugin seam)
   re-enters the queue after the 02 head; grid file can slip without blocking anything.
