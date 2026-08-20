# v1 requirements

The **release contract** for v1 (release 01): what the framework must be able to do, and how that is
verified in this repository. Re-cut 2026-08-20 against the bee-line the
[delivery status](./tickets/README.md) sequences.

This document owns **capability** — what Meteoscape can do for anyone who runs it. What one
deployment *declares* — which offerings at which priority, which secrets, where its composition root
lives, and when it goes live — is [pilot requirements](./pilot-requirements.md)'. The test for which
side a sentence belongs on: **does it survive a second deployment?** If yes it is this document's; if
no it is the pilot's.

It is deliberately **narrow**. Facts with a living owner are cited, never restated — the drift that
made the previous cut wrong came from restating documents that move.

Where the facts this document used to restate actually live — a subset of the
[documentation map](./README.md), kept here because a reader arrives looking for them.

| What you came for | Where it lives |
|---|---|
| Request / response / error contract per surface | [Edge — MCP](./edge/mcp.md), [Edge — embedding](./edge/embedding.md) |
| Canonical parameters, units, vertical carriage | [parameters.md](./parameters.md) |
| Profile declaration, secrets, composition | [architecture § Config, binders, Weaver](./architecture.md#config-binders-weaver), [ADR-0005](./adr/0005-build-time-composition.md) |
| Concrete libraries and toolchain | [`pyproject.toml`](../pyproject.toml), [cicd.md](./cicd.md) |
| Per-work-item criteria, order, delivery state | [delivery status](./tickets/README.md) and the tickets |
| Why the product exists and where it is going | [product roadmap](./product-roadmap.md) |

## Goal

Meteoscape resolves an hourly point forecast from multiple vendors **and from an operator's own
observations and archived forecast runs**, reports how far each vendor sits from that operator's
station measurements, and **corrects for the measured bias** — served through MCP, a supported Python
embedding surface, and HTTP, with retention that survives restart and an account of what each vendor
call cost.

v1 is complete when that path works end to end and is **verified in this repository**. Whether any
particular deployment enables it is that deployment's milestone, not this contract's.

## User stories

Three actors: the **agent** (anything consuming forecasts through a surface — an MCP client, an HTTP
caller, an embedding application), the **embedder** (a Python author building on Meteoscape without a
protocol server), and the **operator** (whoever configures and runs a deployment). One line each —
intent only; the contract detail is the Edge records'.

**Agent**

1. Request an hourly point forecast at a `latitude`/`longitude`, so I answer a weather question
   without integrating each vendor myself.
2. Request only a subset of the parameters, so my answer is scoped to what I need.
3. Give a free `start`/`end` window, so I control the extent without learning per-provider limits.
4. Get every value in a canonical unit, so I compare without per-vendor unit handling.
5. Get per-parameter provenance and `expiration`, so I know which source produced each value and how
   fresh it is.
6. Get the best obtainable source per parameter with automatic fallback, so one vendor outage does
   not break my request.
7. Get a forecast at my exact lat/lon even off a provider's grid, so I do not interpolate myself.
8. Get the producible subset when some parameters cannot be served, so one unavailable parameter does
   not fail the whole request.
9. Get failures as typed errors, so I react correctly — fix my input, drop the parameter, or retry.
10. Read the available envelope before calling, so I know what I can ask for.
11. Tell a corrected value from a raw one by its provenance, so I know a correction was applied and
    on what lineage.

**Operator**

12. Enable, disable, and rank sources at a composition root, so I control quality policy without code
    changes.
13. Have secrets injected at construction, so they never live in code or globals.
14. Have a declared keyed offering without its secret refuse startup, so explicit deployment intent is
    never silently weakened.
15. Have a fully fresh repeat request served without a vendor call, so I minimize latency and vendor
    usage.
16. Keep retention across a restart and share it between processes, so a restart does not re-buy data
    I already paid for.
17. Project my own station observations and archived forecast runs as read-only sources, so my
    private data participates in the same engine.
18. Answer how many vendor calls a deployment spent, against which vendor, over what period.
19. Have a configured vendor budget stop spending past its limit by falling through to the backstop,
    rather than by failing the request.
20. Reach the engine over HTTP, so I can deploy it as a service rather than a local process.

**Embedder**

21. Use a documented, supported Python package surface, so my application resolves forecasts without
    running a protocol server.
22. Handle expected failures through a documented public contract, without importing internal
    exception types.
23. Read per-source, per-parameter bias against the operator's stations, so I can build validation and
    presentation on top of it.

## Standing constraints

What holds **throughout** the release — the things a reader can rely on v1 not doing. These are
positions on seams the contract already carries ([architecture § Extension
points](./architecture.md#extension-points)); each lifts later without a contract change. Anything
that *changes* during the release is a ticket outcome, tracked in the
[delivery status](./tickets/README.md), and is deliberately not here.

- **Timeline realization, no Grid output.** Every request resolves to a single location served as a
  timeline; an off-grid point is answered *at the requested point*, never by emitting a spatial field
  → [architecture § Normalization vs. homogenization](./architecture.md#normalization-vs-homogenization).
- **Selection, never combination.** The `priority` reconciler only: the highest-priority admitted
  producer serves, and a fault falls through wholesale. No consensus, tile, feather, or coverage
  reconciler; no quality scoring; no splicing along `valid_time`.
- **No cross-run combination.** Correction pairs a forecast with an *observation*; two forecast runs
  are never folded into one series →
  [#9](./concerns.md#9-cross-run-combination).
- **One vertical frame.** Every v1 declaration is `above_ground`; the frame tag stays unmodeled until a
  second frame exists (see [Deferrals](#deferrals-v1-records)).
- **Point requests only.** `latitude`/`longitude`; place-name and geocoding are not v1.
- **Hourly output resolution.** No `step` input, no windowed statistics, no sub-hourly →
  [#15](./concerns.md#15-coarser-grid-resampling-and-aggregation-semantics).
- **Null Gateway.** The caller-policy boundary runs its pass-through policy — no authz, quota, or
  rate limiting → [architecture § Gateway](./architecture.md#gateway--caller-policy-boundary).

## Release criteria

Only what **spans tickets** — what no single work item can be accountable for. Per-ticket criteria
live in the tickets, and the release closes when both are met.

1. **The surfaces agree.** MCP, the embedding surface, and HTTP return equivalent product semantics for
   the same ask, exercised against one composition — not three independently asserted contracts.
2. **Correction is validated, not merely computed.** Corrected values are produced end to end and
   checked against the operator's existing analysis through an **independent parity reference** (no
   shared computation code), within the tolerance the correction align declares.
3. **Private sources are first-class.** Station observations and archived forecast runs resolve through
   the same projection algebra as vendor sources, carry provenance naming their origin, and reach the
   operator's database **read-only by construction**.
4. **Vendor spend is accounted.** Every outbound vendor call is counted at the Source seam and
   attributable to vendor and period; a configured budget stops spending past its limit without
   failing the request.

## Out of scope for v1

What a reader may expect here and will not find. Each is a seam the architecture already carries, not
a gap in it.

- **Per-parameter multi-source assembly**, **per-parameter absence reasons and partial success**, and
  **structured resolution logging** — release 02, by the 2026-08-18 boundary.
- **Consensus, disagreement, and confidence products** — [roadmap Phase 3](./product-roadmap.md).
- **Grid realization** and spatial field output.
- **Cross-run combination** → [#9](./concerns.md#9-cross-run-combination).
- **User-defined derived parameters** beyond the wind views and correction — dewpoint, heat index, and
  the composable-DAG surface are [roadmap Phase 4](./product-roadmap.md).
- **Place-name geocoding**, **CoverageJSON**, and a request `format` selector → `ideas.md`.
- **Windowed statistics** and sub-hourly resolution →
  [#15](./concerns.md#15-coarser-grid-resampling-and-aggregation-semantics).
- **A hosted cloud product** — [roadmap Phase 8](./product-roadmap.md).

**No longer out of scope**, against the previous cut: archives, a persisting `Store`, HTTP transport,
vendor quotas and rate limits, and **origin synthesis**. Correction is a method-bearing derivation, so
it mints a synthetic origin and the edge serializer stops being pinned to the atomic path — the seam is
already described by [ADR-0003](./adr/0003-provenance-and-origin.md) and needs no amendment to be used.

## Deferrals v1 records

Deferrals whose **precondition** is worth stating once, rather than rediscovering.

- **Vertical reference is unmodeled in v1 — single-frame by construction.**
  [ADR-0002](./adr/0002-data-model.md) requires the Z axis to carry one axis-level
  **`vertical_reference`** (`above_ground` / `isobaric` / `height_above_msl`), and the implementation's
  `Axis` / `GridDomain` carry no such property. v1 is **entirely `above_ground`** — every declaration
  (2 m, 10 m, surface, the `[0, TOA]` column) shares that datum — so the attribute would be a constant
  nothing reads, and its absence changes no v1 behaviour.
  **The precondition it guards:** the slot must exist *before* any parameter in a **second frame**
  (soil depth, isobaric levels, flight levels) is declared. Z admission compares extents
  **numerically**, so without the tag `1000 hPa` would match `1000 m above ground` — a silent,
  physically meaningless admission of exactly the kind ADR-0002 rules out ("not linearly comparable";
  cross-frame conversion is a Calculator, not a resampler). No roadmap phase introduces a second frame,
  so the trigger is the **first such parameter**, and the slot must be built with that parameter rather
  than in v1. Absorbing it later is additive but not free — it touches the core geometry types and
  every Domain construction site, and `matches` must compare references before extents.
- **Single-flight coalescing** of concurrent same-key refills — already a `Reservoir` seam in
  [ADR-0004](./adr/0004-producer-resolution-and-capability.md); built when contention warrants.
- **A capabilities-introspection surface** — v1 narrates the resolved envelope in the tool description
  instead → [#29](./concerns.md#29-narrated-reach-what-a-profile-promises).
- **Resampler sophistication** beyond v1's identity read-back — parameter-specific resamplers, accuracy
  bounds, and a provider `exact` capability →
  [#5](./concerns.md#5-read-time-homogenization-fidelity).
- **A provider-real freshness signal**, versus the static cadence-model `{Δ, L}` estimate → `ideas.md`.
