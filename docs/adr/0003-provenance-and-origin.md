---
status: accepted
---

# Provenance & origin — per-parameter, atomic or synthetic

A Coverage's metadata model: how provenance attaches to data, and what it means for a value to be
derived. The container that carries it is the [data model](./0002-data-model.md); the composites that
produce synthetic origins are the [algebra](./0001-manifold-algebra-and-composition.md) and
[ADR-0004](./0004-producer-resolution-and-capability.md).

## Decision

A Coverage carries **one `ParameterData` per parameter**, and **provenance is per-parameter** — one
provenance per `ParameterData`, uniform along its geometry, and **not** a coordinate axis. A
`ParameterData`'s **origin** is either **atomic** (a single upstream fetch, authored in full at fetch — carrying the **run identity `issue_time`**, the forecast issuance the values came from) or
**synthetic** (derived from multiple **parent** provenances, whose contributed sub-domains form its
**lineage**, each parent carrying its own `issue_time`). `issue_time` is a **provenance stamp, not a Domain axis** ([ADR-0002](./0002-data-model.md)). **Freshness** is read off `expiration`: a `ParameterData` is **fresh** while
`expiration > now`, and a **synthetic** one's `expiration` is the **worst-case (`min`)** of its parents
(freshness inheritance). The provenance attribute is **geometry-aligned**, so **per-point provenance is a
non-breaking future extension** (realized concretely as `ProvenanceField`, below). "One provider per
parameter" is the special case of **"one provenance per `ParameterData`, origin possibly synthetic."**

## Why

- A `ParameterData` derived by a Calculator and one combined by a coverage `reconciler`
  ([ADR-0004](./0004-producer-resolution-and-capability.md)) are the **same thing** — a synthetic origin
  — so no new metadata shape is needed; composites already produce them.
- Composite-per-parameter captures multi-origin reality (lineage) **without** the per-point tax:
  freshness and residual narrowing stay per-parameter.
- A view that retains only the latest data per parameter is trivially single-origin on the common path.

## Guardrails (keep it additive)

1. Provenance is a **geometry-aligned attribute realized uniformly**, so per-point is purely additive.
2. A synthetic origin's lineage records **each parent's contributed sub-domain** (one bound per parent),
   so segment boundaries are explicit and time-stable.

## Realization: `ProvenanceField`

The "geometry-aligned, realized uniformly, per-point additive" promise is realized concretely as a
**`ProvenanceField`** on each `ParameterData` — an interface with representations that differ only in
**cardinality across cells**, so "one provenance for the whole parameter" and "one per cell" are the
**same shape**:

```python
class ProvenanceField(ABC):
    @property
    def summary(self) -> Provenance: ...    # parameter-level handle — ALWAYS O(1)
    @property
    def uniform(self) -> bool: ...          # True ⇒ summary holds for every cell
    def at(self, i: int) -> Provenance: ... # exact per-cell; opt-in, only when attribution is needed

class Uniform(ProvenanceField):             # cardinality 1 — v1, priority, tile-at-parameter-level
    value: Provenance                       # summary = value; uniform = True; at(i) = value

class PerPoint(ProvenanceField):            # cardinality N — consensus / feather (future)
    summary_: Provenance                    # precomputed synthetic rollup; uniform = False
    values: Sequence[Provenance]            # positional to domain.enumerate(); at(i) = values[i]
```

- **`summary` is the parameter-level handle, always O(1).** The **producer** builds it at construction
  (a reconciler that blends already knows its parents), never the reader at access time — so freshness
  and "who produced this" never scan cells. A `PerPoint` summary is a **synthetic `Provenance`** (origin
  = `synthetic(distinct parents)`, `expiration = min` over cells, per guardrail above), so a blended
  parameter's provenance is itself just a synthetic origin — no new concept.
- **Three access tiers, only the last touching cells:** `summary` (O(1): origin incl. `issue_time`, `fetched_at`,
  `expiration`) → `summary.origin.lineage` (O(parents): distinct parents + each one's contributed
  sub-domain — coarse "which model where" without scanning) → `at(i)` (O(1) per query: exact per-cell).
- **A cell blended from several parents** needs no new shape: that cell's `Provenance` carries a
  **synthetic** origin whose lineage lists the parents (guardrail 2 at cardinality N).

## Considered options

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
  `priority` / `tile` reconciler stays `Uniform` / per-sub-`Domain`. v1 builds only `Uniform`.
- A synthetic `ParameterData` re-derives whenever any parent expires (`min` expiration); incremental
  recompute is an unmodeled later optimization ([#11](../concerns.md#11-incremental-synthetic-recompute)).
- A `Reservoir` only ever **spatially fuses its own cache** (cached ∪ freshly-fetched **same-run** units)
  and stays **`Uniform`** / atomic-equivalent: identity is the **run (`issue_time`)**, not the fetch
  moment, so same-run multi-fetch is one origin, not a synthetic blend. It never fuses **along
  `valid_time`**: `assimilate` replaces **whole units**, a unit's window is **single-origin**, and
  combining origins is the **Arbiter's** reconciler — so cross-run / cross-provider timelines never
  coexist in a unit (the older run goes stale first). This same-run spatial fusion is the `Reservoir`'s
  read-back homogenization and is **in v1** ([#5](../concerns.md#5-read-time-homogenization-fidelity),
  freshness [#4](../concerns.md#4-issue_time-definition)); only the kernel sophistication stays deferred.
- The `ParameterData` container layout (positional `values` / `present`, `unit` / `aggregation`) is the
  [data model](./0002-data-model.md); this ADR owns only the provenance attribute it carries.
