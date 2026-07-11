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
authored in full at fetch — carrying the **run identity `issue_time`**, the forecast issuance the values
came from — **forecast-only**: an **observation** is run-free, so `issue_time` is absent and its `expiration` is effectively **∞**, a bounded revision window for late / QC data deferred alongside observations) or **synthetic** (derived from multiple **parent** provenances, whose contributed sub-domains
form its **lineage**, each parent carrying its own `issue_time`). `issue_time` is a **provenance stamp,
not a Domain axis** ([ADR-0002](./0002-data-model.md)). **Freshness** is read off `expiration` (per
parameter, via `summary`): **fresh** while `expiration > now`, and a **synthetic** origin's `expiration`
is the **worst-case (`min`)** of its parents (freshness inheritance); its `summary` `issue_time` likewise takes the **`min`** over parents (the oldest run; per-parent detail in `lineage`). v1 builds **`Uniform`** (a
single-fetch Source — one origin for the whole Coverage) and **`PerParameter`** (the assembled best view
— one single-origin slice per parameter); **`PerPoint`** (origin varying over geometry — the
parameter × point corner) is the additive seam. "One provider per parameter" is the special case of
**"one origin per parameter, possibly synthetic."**

**Origin identity.** An atomic origin names its producer by a structured **`SourceKey`** (`provider` +
`dataset`) — not a bare string — shared with config/`SourceRegistry` identity and rendered as the SourceRegistry /
config token (→ [glossary: SourceKey](../glossary.md); defined in `identity.py`). Derived at build from
`ProviderManifest.provider_id` + `OfferingSpec.name` (or Provider-authored on expand). `dataset` is **always named** (never a partial
provider-only identity; the default offering is impl-supplied — v1 Open-Meteo → `best_match`), so a stamp
is unambiguous; dataset-level candidacy is [ADR-0004](./0004-producer-resolution-and-capability.md). **Native fidelity is not a provenance
field**: after read-back homogenization the Coverage's `Domain` is the request lattice, and the offering's
native resolution is recoverable server-side from the `SourceKey`. Ranking of multi-resolution offerings
reads the footprint Domain's axis **`step`s**
(→ [ADR-0002](./0002-data-model.md); build [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)) — never a free
`native_resolution` string, and never a parallel provenance / Capability `Resolution` bag.

## Run identity & freshness — the cadence

`issue_time` is the **model run (reference) time in UTC** — the cycle the values came from, the run's
identity — **not** publication time or the assimilation window. A forecast Source declares a per-provider
**`CadenceDef`** `{cadence Δ, publication_latency L, max_lead}`; everything time-relative derives from one
**effective run anchor** at request time `now`:

```
A(now) = floor(now − L, Δ)      # latest run whose publication (r + L) has already passed
```

- **`issue_time` = `A`** — stamped on the atomic `Origin`.
- **`expiration` = `A + Δ + L`** — when the *next* run publishes and supersedes (fresh while
  `now < expiration`), replacing a `fetched_at`-relative TTL, so two fetches of one run expire together
  (a synthetic origin still inherits the parents' `min`, per Decision).
- the leaf's footprint **forward edge** = `A + max_lead` — the capability half, encapsulated in the
  continuous footprint `Domain` ([ADR-0002](./0002-data-model.md) /
  [ADR-0004](./0004-producer-resolution-and-capability.md)).

Each run reigns over `[A + L, A + Δ + L]`, so runs tile with no gap or overlap, and flooring makes `A` a
**step function** — no boundary flicker. v1 ships a **conservative per-provider default** for `{Δ, L}`;
their concrete values, and preferring a provider's **real** reference / availability signal when it
exposes one, are [#18](../concerns.md#18-clock-anchored-footprint-fidelity).

## Why

- A `ParameterData` derived by a Calculator and one combined by a coverage `reconciler`
  ([ADR-0004](./0004-producer-resolution-and-capability.md)) are the **same thing** — a synthetic origin
  — so no new metadata shape is needed; composites already produce them.
- Composite-per-parameter captures multi-origin reality (lineage) **without** the per-point tax:
  freshness and residual narrowing stay per-parameter.
- A view that retains only the latest data per parameter is trivially single-origin on the common path.

## Guardrails (keep it additive)

1. Provenance is a **plane realized at the cardinality each axis needs** — uniform across parameter
   and/or geometry collapses to O(1) storage, so `PerParameter` (v1) and `PerPoint` are purely additive
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

class PerParameter(ProvenanceField):       # one origin per parameter, geometry-uniform — v1 best view
    by_parameter: Mapping[ParameterId, Provenance]   # summary(p) = at(p, _) = by_parameter[p]

class PerPoint(ProvenanceField):           # origin varies over geometry — consensus / feather (future)
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
- **Per-point (per-coordinate) provenance as the base shape.** Rejected for now: drags freshness and
  residual narrowing to per-point with no present use case; kept reachable as the additive `PerPoint`
  representation.
- **A bare union `Provenance | Sequence[Provenance]` for the slot.** Rejected: pushes a cardinality
  type-check onto every consumer; the `ProvenanceField` interface gives a uniform `summary` / `at(i)`
  regardless of cardinality.
- **Strict one-atomic-provenance-per-parameter, returning combined products as side-by-side Coverages.**
  Rejected: pushes "seamless timeline" onto every consumer and cannot express derived parameters at all.

## Consequences

- Point-level attribution (a value → a specific parent) is the `PerPoint` representation — required by a
  **`consensus` / `feather`** reconciler ([ADR-0004](./0004-producer-resolution-and-capability.md)); a
  `priority` / `tile` reconciler stays `Uniform` / `PerParameter`. v1 builds `Uniform` + `PerParameter`.
- A synthetic `ParameterData` re-derives whenever any parent expires (`min` expiration); incremental
  recompute is an unmodeled later optimization ([#11](../concerns.md#11-incremental-synthetic-recompute)).
- A `Reservoir` only ever **spatially fuses its own cache** (cached ∪ freshly-fetched **same-run** units)
  and stays **`Uniform`** / atomic-equivalent: identity is the **run (`issue_time`)**, not the fetch
  moment, so same-run multi-fetch is one origin, not a synthetic blend. It never fuses **along
  `valid_time`**: `assimilate` replaces **whole units**, a unit's window is **single-origin**, and
  combining origins is the **Arbiter's** reconciler — so cross-run / cross-provider timelines never
  coexist in a unit (the older run goes stale first). This same-run spatial fusion is the `Reservoir`'s
  read-back homogenization and is **in v1** ([#5](../concerns.md#5-read-time-homogenization-fidelity),
  freshness via the cadence above); only the kernel sophistication stays deferred.
- The `ParameterData` container layout (positional `values` / `present`) and the Coverage's `parameters`
  descriptor block are the [data model](./0002-data-model.md); this ADR owns the provenance plane the
  `Coverage` carries.
