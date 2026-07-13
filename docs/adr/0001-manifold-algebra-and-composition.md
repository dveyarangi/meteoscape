---
status: accepted
---

# The Manifold algebra & composition

Everything below the system's outer boundary is built from a single abstraction — a **Manifold** — so
the many roles it plays are *shapes of one algebra* rather than separate contracts. This ADR fixes the
abstraction (what a Manifold is, its one operation, its `capability` dual, its `Writable` facet) **and** how Manifolds compose
into larger ones (when a new node is justified, how composed nodes evaluate). Concrete shapes — vendor
leaves, `Reservoir`s, the served "best" view — live in [`architecture.md`](../architecture.md); the data
a Coverage carries is the [data model](./0002-data-model.md); provenance is
[ADR-0003](./0003-provenance-and-origin.md); producer resolution is
[ADR-0004](./0004-producer-resolution-and-capability.md).

## The algebra

- **One operation, closed.** A Manifold is a projectable space with exactly one operation:
  `project(selection) -> Manifold`, **closed** (the result is itself a Manifold). A Manifold is a
  **continuous field until sampled**: `project` returns a restricted **view/field**; concrete values
  appear only by **sampling onto an enumerable coordinate set**, and **sampling is just `project` with
  an enumerable Selection** — no separate `sample` / `materialize` verb. ("Continuous field" is a
  *semantic* view over sampleable provider data — projectable / interpolable — **not** a claim of
  analytic continuity; providers are discrete and homogenization interpolates between samples.)

- **`capability` — the dual of `project`.** Alongside `project`, every Manifold exposes a `capability`:
  `project` *consumes* a `Selection`; `capability` *advertises* which Selections are servable
  (`serves(parameter, requested)` + the served `parameters`). It is a **base-`Manifold` member on every
  node**, not a facet — a leaf declares it, a composite **derives it bottom-up** (union of parameter sets;
  AND/OR of the predicate), and a materialized `Coverage` exposes it **co-domained** on its one sampled
  grid (so the Coverage's `domain` derives from it). The family and its matching rules are
  [ADR-0004](./0004-producer-resolution-and-capability.md).

- **Logically read-only.** `project` is referentially transparent **at the value it returns** (same
  Selection ⇒ same Coverage) but **not** referentially pure: it does I/O (a Provider fetches) and may
  populate `Store`s as **transparent memoization** (a fill on a miss changes no answer). It **computes**
  (sample / select / assemble) but mutates **no orchestration or policy state**. There is **no external
  god-orchestrator** above the algebra that decomposes, ranks, or routes; acquisition and selection are
  **properties of particular shapes**, carried as ordinary `project` logic. The single *declared*
  mutation, `assimilate(coverage)`, is **not** on the base abstraction — it is the `Writable` facet.

- **Facets, not subtypes.** Optional behaviour is added by facets (interface segregation), never a
  type hierarchy:
  - **`Writable`** — accepts `assimilate(coverage)`: the **materialization boundary** — sample a view
    onto the node's own grid and store it. Provenance is authored **upstream**, never computed here.
  - A node exposes **no public lattice**: its declared grids (per axis, **provider-exact where a
    vendor declares one, a configured guess for point vendors that expose none**) are **private to
    its `Store`** — the `quantize` / retention / read-back target — and a provider-exact lattice
    reaches the `Store` as a **build-time declaration** at weave, not a request-path read. The only
    public `domain` is the **`Coverage`'s** — the positional grid its `ParameterData` align to,
    derived from its materialized `capability`
    ([ADR-0006](./0006-materialization-granularity-and-store-shape.md)).

- **The output lattice is not carried; it is the Selection's `Domain`.** `Selection = Domain +
  parameters`. A **lattice is simply an enumerable `Domain`**, not a second structure layer. Result
  countability is conferred by the Selection: a **continuous** Domain → an (uncountable) **field**; an
  **enumerable** Domain → a **Coverage**, the materialized leaf (`Coverage <: Manifold`) — the one
  place a public `domain` exists. A node with a store still returns a field for a continuous
  selection. Selection **mode** is the *kind of Domain* (Continuous / Snapped / Enumerable), not a
  separate field — the encoding is the [data model](./0002-data-model.md).

- **Materialization = sampling a field onto an enumerable `Domain`** (`project` with an enumerable
  Selection). A storing `Reservoir` asks its child on a **`quantize`d** Selection (snapped to its **own
  store grid** + widened to whole units; that grid is a **fidelity floor**) and `assimilate`s the result
  **a whole unit at a time**, then **homogenizes the store grid onto the requested `Domain` at read** —
  because `project(sel)` must return a Coverage on **`sel.domain`**. So for a storing node homogenization
  is **intrinsic and two-sided** — write: child→grid; read: grid→request — degenerating to **identity**
  when the request already lands on the grid (a snapped read is a **crop**); a non-storing leaf samples
  its substrate per read straight to the target. **Spatially fusing cached ∪ freshly-fetched same-run
  units is the same read homogenization.** **Freshness is read-time**, evaluated per read off each
  parameter's provenance `expiration` (the Coverage plane's `summary(parameter)`; the freshness model,
  including synthetic-origin inheritance, is [ADR-0003](./0003-provenance-and-origin.md)); `assimilate` is **pure storage** (never recomputes
  provenance), so the algebra needs no `is_current` operation. The **kernel choice / accuracy bounds** of
  the homogenization stay deferred ([concern #5](../concerns.md#5-read-time-homogenization-fidelity)).

## Composition

- **Leaf vs composite.** A Manifold is either a **leaf** — backed by its own **substrate**, which its
  `project` samples directly — or a **composite** — defined over **child Manifolds + a combine rule**,
  owning no substrate. A composite's children are **injected at construction** (no lookup at `project`
  time); its `project` forwards the Selection to children with the **parameter set rewritten** to the
  inputs it consumes — **`Domain` (and its shape) unchanged** — then combines the results. This
  structural axis is **orthogonal** to the *origin* axis (atomic vs synthetic,
  [ADR-0003](./0003-provenance-and-origin.md)). The **`Reservoir` is the one composite that re-grids its
  child**: it projects the child on a **store-shaped** Selection (`store_shape` = the request `quantize`d
  — snapped to the grid and widened to whole units) for retention and **homogenizes back onto the request
  at read** (above) — whereas pass-through composites (the Arbiter, Calculators) keep the **`Domain`
  unchanged** and only rewrite parameters.

- **Compose for behaviour; the coverage axis is a reconciler, not a node.** Mint a **new composite only
  when children differ in behaviour** (retention / population policy, or `project` logic). Children that
  differ **only in which `Domain` they cover** are **not** a new node — that is a coverage `reconciler`
  on the Arbiter ([ADR-0004](./0004-producer-resolution-and-capability.md)). Selection is the degenerate
  reconciler.

- **Composites are lazy fields; intermediates are transient.** A pass-through composite chain composes
  **fields**; nothing materializes until an enumerable Selection reaches the data-owning **leaves**,
  which each sample their substrate **once**, straight to the target — **a storing `Reservoir` is the
  exception**, interposing its store grid and a read-time homogenization (above). Intermediates
  are **transient values over the one shared output lattice** — not surfaces, nodes, or `Store` entries.
  A **pointwise** composite is **grid-free**; a **stencil** composite — the home of **differential
  operators** (gradient, divergence, vorticity, advection, tendency) — allocates a **local, transient
  working grid** (output lattice + **halo**). These operators run on the **curved** spatial manifold, so
  the **`Domain` carries the metric** (sphere map factors) that homogenization and stencils apply.

- **Storing an intermediate is opt-in and isolated.** Persisting or sharing an intermediate promotes it
  to a **named node** wrapped in **its own** `Reservoir` — never a shared serving `Store`. Sharing
  across composites is the **same node instance** in the graph.

- **Derived parameters are generic composites.** A Calculator deriving a parameter from input parameters
  is **one generic composite** parameterized by an **output⟸input parameter mapping** and a function —
  **no class per formula** — and is **itself the derived field**. It emits a **synthetic origin**
  ([ADR-0003](./0003-provenance-and-origin.md)); its topology relative to the Arbiter is
  [ADR-0004](./0004-producer-resolution-and-capability.md).

- **Parameters stay first-class in the `Selection`.** `project` takes `Selection = Domain + parameters`;
  parameters are **never folded into the `Domain`** as a non-interpolable tag-set. This is exactly what
  lets a composite **rewrite only the parameter set** it consumes while the `Domain` passes through
  unchanged.

## Why

- One deep interface plus two facets replaces a contract-per-role; composition then yields new behaviour
  with **no contract change**, and earns its keep only where it isolates genuinely different
  **behaviour** (coverage differences are a filter, not a node).
- `-> Manifold` is **real**: views and derived chains are genuine uncountable **fields**; countability
  appears only in a materialized result under a finite selection. The narrowing operations (parameter split,
  residual `Domain`) are **uniform** over continuous and enumerable Domains — no lattice to drag through.
- Purity keeps a coordination / policy layer **out** of the algebra: acquisition and selection are
  pushed **down** into concrete shapes, not lifted into a god-module. Lazy evaluation avoids an
  eager-materialization tax and hidden writes; retention is reserved for **shared or expensive** nodes.
- A new derived parameter is **data** (a mapping + a function), not a new type; combination is
  composition at construction + `project`, so the algebra needs no `combine([Manifold])` verb.

## Considered options

- **A contract per role.** Rejected: the apparent differences are degenerate cases of one projectable
  shape — duplicated surface.
- **A central orchestrator that decomposes / ranks / routes / assembles.** Rejected: a god-module that
  pulls policy above the computational layer. Acquisition is a property of a *shape*.
- **A separate `materialize()` / `sample()` verb, or a `combine([Manifold])` verb.** Rejected:
  materialization is `project` with an enumerable Selection; combination is `project` over injected
  children.
- **A mandatory lattice on the request (`Selection = Domain + structure`).** Rejected: forces a lattice
  onto every request and narrowing op, makes `-> Manifold` cosmetic, and double-sources the lattice
  against stored grids. A **global canonical-lattice config** is likewise rejected — the canonical
  lattice is **emergent** from whichever node stores / serves.
- **A node per data-kind / per region; eager materialization / storing every intermediate; per-formula
  Calculator subclasses.** Rejected: each duplicates a filter or adds a tax / hidden state for what is a
  coverage difference, a lazy field, or parameterized data.

> **Shapes (illustrative, not part of the algebra).** Concrete nodes — a vendor leaf, a `Reservoir`, the
> Arbiter, the served "best" view, Calculators — differ only in `project` logic and which facets
> they add; see [`architecture.md`](../architecture.md).
