---
status: accepted
---

# Provenance & origin — a Coverage plane, atomic or synthetic

A Coverage's metadata model: how provenance attaches to data, and what it means for a value to be
derived. The container that carries it is the [data model](./0002-data-model.md); the composites that
produce synthetic origins are the [algebra](./0001-manifold-algebra-and-composition.md) and
[ADR-0004](./0004-producer-resolution-and-capability.md).

## Decision

A Coverage carries **one provenance plane** — a `ProvenanceField` peer to `domain` and `ranges`
([ADR-0002](./0002-data-model.md)), **not** a coordinate axis and **not** a per-`ParameterData`
attribute. It is indexed over **two** axes — **parameter** (the Arbiter picks a source per parameter)
and **geometry point** (a mosaic differs per cell) — read `at(parameter, i)`, with `summary(parameter)`
the **O(1) per-parameter handle**. A value's **origin** is either **atomic** (a single upstream fetch,
authored in full at fetch — carrying the forecast revision identity `issue_time`: a real run time or,
for a runless provider, a Fetch bucket — **forecast-only**: an **observation** is run-free, so
`issue_time` is absent and its `expiration` is effectively **∞**, with a bounded revision window for
late / QC data deferred alongside observations) or **synthetic** (a composite's record of a derivation — its **lineage** of contributing parents, each
carrying its own `issue_time`, plus a **calculation-method** tag for a computed output). **Synthesis is
not gated on parent count**: a method-bearing derivation mints a synthetic origin even over a *single
shared-origin* input (the method is what it records). Conversely, a derivation that **preserves its input
unchanged** — a lossless, invertible transform — **propagates** that input's origin verbatim rather than
minting one (nothing to record, and a lone shared origin passes through). A blend across ≥2 distinct
origins is always synthetic. `issue_time` is a **provenance stamp,
not a Domain axis** ([ADR-0002](./0002-data-model.md)). **Freshness** is read off `expiration` (per
parameter, via `summary`): **fresh** while `expiration > now`, and a **synthetic** origin's `expiration`
is the **worst-case (`min`)** of its parents (freshness inheritance); its `summary` `issue_time` likewise takes the **`min`** over parents (the oldest run; per-parent detail in `lineage`). **`Uniform`** represents a
single-fetch Source — one origin for the whole Coverage — and **`PerParameter`** represents an assembled
view with one single-origin slice per parameter; **`PerPoint`** (origin varying over geometry — the
parameter × point corner) is the additive seam. "One provider per parameter" is the special case of
**"one origin per parameter, possibly synthetic."**

**Origin identity.** An atomic origin names its producer by a structured **`SourceKey`** (`provider` +
`dataset`) — not a bare string — shared with config/`SourceRegistry` identity and rendered as the SourceRegistry /
config token (→ [glossary: SourceKey](../glossary.md); defined in `identity.py`). Derived at build from
`ProviderManifest.provider_id` + `OfferingSpec.name` (or Provider-authored on expand). `dataset` is **always named** (never a partial
provider-only identity; the default offering is implementation-supplied — for example, Open-Meteo → `best_match`), so a stamp
is unambiguous; dataset-level candidacy is [ADR-0004](./0004-producer-resolution-and-capability.md). **Native fidelity is not a provenance
field**: after read-back homogenization the Coverage's `Domain` is the request lattice, and the offering's
native resolution is recoverable server-side from the `SourceKey`. Ranking of multi-resolution offerings
reads the footprint Domain's axis **`step`s**
(→ [ADR-0002](./0002-data-model.md); build [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)) — never a free
`native_resolution` string, and never a parallel provenance / Capability `Resolution` bag.

**Origin identity and declared provenance (2026-08-21 amendment, Mongo obs source align).** An
atomic origin may carry three optional identity fields beyond its `SourceKey` — **`authority`**
(who stands behind the values: a station network's owner, a WMO centre, a vendor), **`process`**
(how they were made: model id and version, blend, instrument method, climatology base period), and
**`unit`** (which instance of the producing system, where the type has instances: a station, a
satellite platform, a radar site, an ensemble member). Plain optional strings on `AtomicOrigin` —
no sub-record and no vocabulary beside provenance; stress-tested against the corpus's source-type
roster (vendor APIs, station networks, archive runs, radar, satellite, internal models, GRIB/ARCO,
normals) and nothing needed a fourth field. Run identity stays **`issue_time`**, never an identity
field. **`unit` is the instance's meaningful identity in the authority's namespace** — a station's
name or the network's own station id — never a value derivable from the request itself, and never
an alias dump: alternate ids (WMO / ICAO / local) are registry metadata, not stamps. Precedent: the
WMO identification section (centre / subCentre / generatingProcess), subCentre folding into the
`authority` path and versions into `process`.

**The declaration side of the same seam.** `Capability.origins(parameter)` publishes **declared
provenance over the reach**: a sequence of (sub-domain, `AtomicOrigin`) pairs naming which origin
would serve where — empty when nothing is declared (the honest default), a single whole-reach entry
for a one-origin producer, one entry per instance for a scatter-shaped one (the
`Uniform`/`PerPoint` ladder, declaration side). This is how a request-forming consumer learns
*what can be requested and from whom, paired*, before any request. A declared origin omits what is
not yet knowable — for a live vendor that includes `issue_time`, while an archive declaring
retained runs may honestly carry it; the served stamp is authored at fetch, from the documents
and the addressing that read them, and normally equals its declaration — divergence is visible
evidence, never papered over. First filler: the
[Mongo obs source](../tickets/01-0124-mongo-obs-source.md) — authority = the network, process =
the method, unit = the station's name / network id.

## Run identity, Fetch buckets, and freshness — the cadence

`issue_time` is the Source's forecast-revision identity in UTC — a real model run time where the
producer publishes runs, otherwise a Fetch bucket anchor. It is **not** publication time or a Domain
axis. A forecast Source declares a per-provider **`CadenceDef`**
`{cadence Δ, publication_latency L, max_lead, shelf?}`. In the **run regime**, identity and
freshness derive from the latest effective run anchor at request time `now`:

```
A(now) = floor(now - L, Δ)      # latest run whose publication (r + L) has already passed
```

- **`issue_time` = `A`** — stamped on the atomic `Origin`.
- **`expiration` = `A + Δ + L`** — when the *next* run publishes and supersedes (fresh while
  `now < expiration`), replacing a `fetched_at`-relative TTL, so two fetches of one run expire together
  (a synthetic origin still inherits the parents' `min`, per Decision).
- the leaf's footprint **availability window** = `[W, W + max_lead]`, where
  `W = floor(now, shelf)` when a **Shelf** is declared (a shelf-anchored product — e.g. a
  by-calendar-day vendor), else `W = A` (the run's own forecast window). Two clocks: the run clock
  keeps identity and freshness; the shelf, when present, anchors only what is *servable* — the window
  advances one shelf at a time, so **`max_lead` is the window's length and the shelf is the size of
  the jumps its start makes**; Reach is where it stands now. Encapsulated
  in the continuous footprint `Domain` ([ADR-0002](./0002-data-model.md) /
  [ADR-0004](./0004-producer-resolution-and-capability.md)) — declared by the vendor leaf, executed
  by the shared axis, never consulted by the `Reservoir`, whose refetch is governed by expiration and
  the retention predicate alone.

  **`W` is a phase declaration, not merely an opening time — so it must sit on a shelf boundary.**
  Materializing the rolling window anchors the lattice *at `W`* (`RegularAxis(name, W, step, …)`), so
  `W` states **which phase the vendor's ticks sit on**. An off-boundary `W` — `now` itself, say —
  would put the lattice on an arbitrary sub-step phase, which is the off-phase case
  [#21](../concerns.md#21-serves-extent-vs-project-crop-ability) calls genuinely unimplementable by
  index arithmetic; it would also stop `W` being a **step function**, so admission and narration would
  flicker between two clock reads. *Which* boundary is a separate question — flooring is the shipped
  choice, and a vendor whose series begins later than its boundary is declared **early** rather than
  off-phase. The resulting leading-edge over-declaration is absorbed by retention, not by the
  declaration
  ([ADR-0002 § the two predicates](./0002-data-model.md#the-two-predicates-admission-and-retention)).

  **The cadence must not exceed `max_lead`** — because the polling promise must be keepable, not
  because anything becomes unservable: a held window that falls behind `now` is quietly refilled by
  the retention predicate. What actually breaks is governance: those rescue refills are vendor
  calls the cadence never scheduled, so `max_lead` — not Δ — starts driving spend (measured: a 5 h
  window under a 12 h cadence buys 5 calls/day where the cadence promises 2), and each one serves
  data before the `expiration` the edge narrated, making `exp` false in the direction it promises.
  A cadence longer than the window is therefore an incoherent configuration, refused at
  construction.

Each run reigns over `[A + L, A + Δ + L]`, so runs tile with no gap or overlap, and flooring makes `A` a
**step function** — no boundary flicker. A provider may supply conservative defaults for `{Δ, L}`;
their concrete values, and whether to prefer a provider's **real** reference / availability signal when it
exposes one, are [#18](../concerns.md#18-clock-anchored-footprint-fidelity).

### Run and bucket regimes

The formulas above describe the **run regime**. Gridded NWP products and reanalysis slices carry a
real reference time; where a vendor exposes one, it is preferred over a computed anchor
(→ [ideas: freshness](../ideas.md#freshness)).

A provider that publishes no run schedule uses the **bucket regime**. `A` is then the **Fetch
bucket** — the Δ-wide window the fetch fell in — rather than a claim that a run occurred:

- **`L = 0`.** Publication latency is *run time → available*; with no run there is nothing to be latent
  from, and a non-zero `L` would slide the bucket off the grid its own identity is defined on.
- **`A = floor(fetched_at, Δ)`** — which is the same formula, with `L = 0`. Two fetches in one bucket
  share an `issue_time`, preserving the property anchoring exists for.
- **`Δ` is the deployment's polling interval**, not an observed vendor cadence.
- **`expiration = A + Δ` stays anchored.** With no real event at the grid line, the effective TTL
  sawtooths and averages `Δ/2` → [#18](../concerns.md#18-clock-anchored-footprint-fidelity).

The regime is a per-provider fact; one deployment may use both. Any consumer that requires a true run
identity must distinguish or decline Fetch buckets rather than interpret them as runs.

## Why

- A `ParameterData` derived by a Calculator and one combined by a coverage `reconciler`
  ([ADR-0004](./0004-producer-resolution-and-capability.md)) are the **same thing** — a synthetic origin
  — so no new metadata shape is needed; composites already produce them. The exception is a derivation
  that **preserves its input unchanged** (a lossless, invertible transform): it **propagates** the input's
  origin rather than minting a synthetic one. Synthesis tracks the *method*, not the input count.
- Composite-per-parameter captures multi-origin reality (lineage) **without** the per-point tax:
  freshness and residual narrowing stay per-parameter.
- A view that retains only the latest data per parameter is trivially single-origin on the common path.

## Guardrails (keep it additive)

1. Provenance is a **plane realized at the cardinality each axis needs** — uniform across parameter
   and/or geometry collapses to O(1) storage, so `PerParameter` and `PerPoint` are purely additive
   over `Uniform`.
2. A synthetic origin's lineage records **each parent's contributed sub-domain** (one bound per parent),
   so segment boundaries are explicit and time-stable.

## Realization: `ProvenanceField`

The plane is realized concretely as a **`ProvenanceField`** on the `Coverage` — an interface whose
representations differ only in **which axes (parameter, geometry) they vary over**, so "one origin for
the whole Coverage", "one per parameter", and "one per cell" are the **same shape**:

```python
class ProvenanceField(ABC):
    def summary(self, parameter) -> Provenance: ...   # per-parameter handle — ALWAYS O(1)
    def at(self, parameter, i) -> Provenance: ...     # exact per (parameter, point); opt-in

class Uniform(ProvenanceField):            # one origin, whole Coverage — single-fetch Source
    value: Provenance                      # summary(_) = at(_, _) = value

class PerParameter(ProvenanceField):       # one origin per parameter, geometry-uniform assembled view
    by_parameter: Mapping[ParameterId, Provenance]   # summary(p) = at(p, _) = by_parameter[p]

class PerPoint(ProvenanceField):           # origin varies over geometry — consensus / feather
    ...                                    # summary(p) = synthetic rollup; at(p, i) = per-cell
```

- **`summary(parameter)` is the per-parameter handle, always O(1).** The **producer** builds it at
  construction (a reconciler that blends already knows its parents), never the reader at access time —
  so freshness and "who produced this" never scan cells. A `PerPoint` summary is a **synthetic
  `Provenance`** (origin = `synthetic(distinct parents)`, `expiration = min` over cells, per guardrail
  above), so a blended parameter's provenance is itself just a synthetic origin — no new concept.
- **Three access tiers, only the last touching cells:** `summary(p)` (O(1): origin incl. `issue_time`,
  `fetched_at`, `expiration`) → `summary(p).origin.lineage` (O(parents): distinct parents + each one's
  contributed sub-domain — coarse "which model where" without scanning) → `at(p, i)` (O(1) per query:
  exact per-cell).
- **A cell blended from several parents** needs no new shape: that cell's `Provenance` carries a
  **synthetic** origin whose lineage lists the parents (guardrail 2 at cardinality N).

## Considered options

- **Provenance as a per-`ParameterData` attribute.** Rejected: origin varies by *both* parameter and
  geometry point, and the Arbiter assembles one Coverage from many single-origin sources — so it is a
  Coverage-level plane, and a per-slice field would force a rewrite of each slice on assembly.
  `PerParameter` is the per-parameter view as one plane representation.
- **Per-point (per-coordinate) provenance as the base shape.** Rejected as the base: drags freshness and
  residual narrowing to per-point for every Coverage; kept reachable as the additive `PerPoint`
  representation.
- **A bare union `Provenance | Sequence[Provenance]` for the slot.** Rejected: pushes a cardinality
  type-check onto every consumer; the `ProvenanceField` interface gives a uniform `summary` / `at(i)`
  regardless of cardinality.
- **Strict one-atomic-provenance-per-parameter, returning combined products as side-by-side Coverages.**
  Rejected: pushes "seamless timeline" onto every consumer and cannot express derived parameters at all.

## Consequences

- Point-level attribution (a value → a specific parent) is the `PerPoint` representation — required by a
  **`consensus` / `feather`** reconciler ([ADR-0004](./0004-producer-resolution-and-capability.md)); a
  `priority` / `tile` reconciler stays `Uniform` / `PerParameter`.
- A synthetic `ParameterData` re-derives whenever any parent expires (`min` expiration); incremental
  recompute is an unmodeled optimization ([#11](../concerns.md#11-incremental-synthetic-recompute)).
- A `Reservoir` only ever **spatially fuses its own Holdings** (retained ∪ freshly fetched,
  **same revision group**)
  and stays **`Uniform`** / atomic-equivalent: identity is the **revision group (`issue_time`)**, not the fetch
  moment, so Holdings sharing an `issue_time` are one origin, not a synthetic blend. It never fuses **along
  `valid_time`**: `assimilate` replaces **whole Holdings**, a Holding's window is **single-origin**, and
  combining origins is the **Arbiter's** reconciler — so cross-revision / cross-provider timelines never
  coexist in one Holding (the older revision goes stale first). This same-revision spatial fusion is the `Reservoir`'s
  read-back homogenization ([#5](../concerns.md#5-read-time-homogenization-fidelity), freshness via
  the cadence above); Resampler sophistication remains a separate decision.
- The `ParameterData` container layout (positional `values` / `present`) and the Coverage's `parameters`
  descriptor block are the [data model](./0002-data-model.md); this ADR owns the provenance plane the
  `Coverage` carries.
