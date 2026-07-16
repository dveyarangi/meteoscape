# RFC 0001 — Derived wind calculator (ticket 002b)

- **Date:** 2026-07-16
- **Ticket:** [002b — Derived wind calculator](../../tickets/done/002b-derived-wind-calculator.md)
- **Depends on:** 002 (done) — canonical `wind_u` / `wind_v` served by Open-Meteo
- **Status:** Accepted (implemented)
- **Owning docs:** [ADR-0004](../../adr/0004-producer-resolution-and-capability.md) (producer resolution),
  [ADR-0005](../../adr/0005-build-time-composition.md) (build-time composition),
  [ADR-0003](../../adr/0003-provenance-and-origin.md) (provenance propagation)
- **Planning source:** [session 0012 — 002b align](../../sessions/0012-20260714-002b-align-derived-wind.md)
  (the 7 align decisions + the "002b implementation deltas" this RFC turns into a build plan)

> Accepted plan for ticket 002b (implemented). Stages S0–S6 and decisions D1–D3 / F6–F7 below are the
> record of what shipped.

---

## 1. Summary

002b lands three coupled deliverables, in one thread because the derived-wind Calculator is the case
that forces the first multi-node Coverage assembly:

1. **Producer unification + Reconciler extraction** — Sources and Calculators become one
   `Producer{node, key}`; the Arbiter becomes `Arbiter(producers, reconciler)`; priority becomes a
   first-class `Reconciler` built by `build_reconciler`.
2. **Top-Arbiter multi-parameter assembly** — the top Arbiter stitches **disjoint single-parameter
   winners** on the shared domain via a `PerParameter` provenance plane, retiring the current
   "winners not all one node → raise" guard.
3. **A single multi-output wind Calculator** — `{wind_speed, wind_direction}` from `{wind_u, wind_v}`
   via a scoped input Arbiter, `hypot` / `atan2` kernel, and **provenance propagated verbatim** from
   Open-Meteo (no synthesis).

The documentation surface (ticket, ADR-0004, ADR-0005, glossary) is already aligned to this target.
The runtime code still holds the pre-002b shape; this RFC is the code-side plan to catch up.

## 2. Decisions resolved during planning

Three gaps between the accepted ADRs and the code were found and resolved with the ticket owner:

- **D1 — `ParameterTable` injection (Q1 → A).** The wind Calculator's `DerivedCapability` and its output
  Coverage need resolved `ParameterDef`s for `wind_speed` / `wind_direction`, but neither
  `CalculatorBinder.build(defs)` nor `Weaver(stores)` currently holds a `ParameterTable`. **Resolution:**
  `CalculatorBinder.build` gains a `parameters: ParameterTable` argument (mirroring `SourceBinder`);
  `RegisteredCalculator` stores the **resolved output defs**. The Weaver stays purely structural
  (table-free). → doc follow-up F1.

- **D2 — kernel output authorship (Q2 → 2b).** `CombineFn` was `Coverage → Coverage` so a future
  shape-aware calculator could return a *transformed domain*; but the kernel has no `ParameterTable` to
  author `capability.parameters`, and letting it build an empty-params capability is ugly. **Resolution:**
  the kernel returns **`(EnumerableDomain, Mapping[ParameterId, ParameterData])`** — structural payload
  only. The `Calculator` **node** builds the final `CoverageRecord` (capability from its declared output
  defs, provenance propagated, well-formedness validated). This keeps the ADR's domain-transform seam
  open while moving all identity/provenance authorship onto the node. → doc follow-up F2.
  *Relation to session 0012 decision 4:* 0012 settled `fn: Coverage → Coverage` and rejected a
  values-only kernel because a flat array "smuggles the timeline shape into the boundary," blinding
  shape-aware calculators to the domain. 2b **honours that rationale** — the domain stays explicit on
  both sides (`Coverage` in, `(domain, ranges)` out) — while removing the wart 0012 left open: a
  `Coverage`-returning kernel with no `ParameterTable` cannot author `capability.parameters`. So 2b
  refines decision 4's return encoding; it does not reverse its intent.

- **D3 — `Selection` widening (Q3).** ADR-0004's pseudocode `sel.with_params(self.inputs)` cannot work:
  `with_params` (core.py) *rejects* params not already in the selection, and `wind_u` / `wind_v` are
  never in a `{wind_speed, wind_direction}` request. **Resolution:** the Calculator constructs a fresh
  `Selection(sel.domain, self.inputs)` directly. No new `Selection` method. → doc follow-up F3
  (ADR-0004 pseudocode).

## 3. Scope, boundaries, ownership

**In scope (code):** `identity.py`, `config.py`, `nodes/composition.py`, `nodes/arbiter.py`,
`nodes/calculator.py`, `nodes/weaver.py`, `manifold/capability.py` (`DerivedCapability` outputs),
`nodes/catalog/calculators.py` (`CombineFn` type), a new wind-calculator plugin module, `server.py`
wire-up, `api/mcp_app.py` (no change expected — exposure already lists the wind views).

**Contracts touched:**

| Contract | Current | Target |
|---|---|---|
| `Arbiter.__init__` | `(sources: Mapping[SourceKey, Manifold], registry, policy)` | `(producers: Sequence[Producer], reconciler: Reconciler)` |
| Reconciler | inline `_priority_candidates` reading `registry` | first-class `Reconciler` / `PriorityReconciler`, built by `build_reconciler(policy, SourceRegistry, CalculatorRegistry)` |
| `Producer` | — | `Producer{node: Manifold, key: ProducerKey}` (no priority) |
| `ProducerKey` | — | `SourceKey \| CalculatorKey` |
| `CalculatorKey` | — | `CalculatorKey(method, name)` in `identity.py` |
| `CalculatorSpec` | `output`, `inputs`, `fn_id`, `stored` | rename `CalculatorDef`: `outputs`, `inputs`, `fn_id`, `priority`, `name?`, `stored` |
| `RegisteredCalculator` | keyed by `ParameterId`; `output: ParameterId` | keyed by `CalculatorKey`; `key`, `priority`, `outputs: Mapping[ParameterId, ParameterDef]` |
| `CalculatorRegistry` | `Mapping[ParameterId, …]` | `Mapping[CalculatorKey, …]` |
| `CalculatorBinder.build` | `(specs)` | `(defs, parameters: ParameterTable)` |
| `Calculator.__init__` | `(output: ParameterDef, inputs, resolver)` | `(outputs, inputs, fn, resolver)` |
| `DerivedCapability` | `output: ParameterDef` | `outputs: Mapping[ParameterId, ParameterDef]` |
| `CombineFn` | `Callable[[Coverage], Coverage]` | `Callable[[Coverage], tuple[EnumerableDomain, Mapping[ParameterId, ParameterData]]]` |

**Ownership invariants preserved:** the two binders/registries stay distinct (ADR-0005); priority is
recipe data the reconciler interprets, never Weaver logic; the Weaver only wraps nodes as `Producer`s and
*invokes* `build_reconciler`; the graph stays an acyclic DAG (every Calculator edge points down through
its scoped Arbiter).

## 4. Target code shapes

### 4.1 Identity (`identity.py`)

```python
@dataclass(frozen=True)
class CalculatorKey:           # peer of SourceKey; keyed on METHOD, not output
    method: str                # = CalculatorManifest.fn_id
    name: str                  # configured variant; binder-defaulted when omitted
    def __str__(self) -> str: return f"{self.method}:{self.name}"

ProducerKey = SourceKey | CalculatorKey
```

Two same-output / different-method calculators are therefore **distinct competing producers**, exactly
as two providers competing for a parameter.

### 4.2 Producer + Reconciler (`nodes/arbiter.py`, or a small `nodes/producer.py`)

```python
@dataclass(frozen=True)
class Producer:                       # neutral ranked candidate — NO priority field
    node: Manifold                    # Reservoir(store, Provider) | Calculator | Reservoir(store, Calculator)
    key: ProducerKey

class Reconciler(Protocol):
    def select(self, parameter: ParameterId,
               candidates: Sequence[Producer]) -> Sequence[Producer]: ...

@dataclass(frozen=True)
class PriorityReconciler:             # holds a bare lookup, not the registries
    priority: Mapping[ProducerKey, int]
    def select(self, parameter, candidates):  # lower wins; bind order breaks ties
        return sorted(candidates, key=lambda p: self.priority[p.key])

def build_reconciler(policy, sources: SourceRegistry,
                     calcs: CalculatorRegistry) -> Reconciler:
    if policy.default_reconciler != "priority":
        raise CompositionError(...)   # v1 ships only priority
    priority = {k: r.priority for k, r in sources.sources.items()}
    priority |= {k: r.priority for k, r in calcs.calculators.items()}
    return PriorityReconciler(priority)
```

### 4.3 Arbiter (`nodes/arbiter.py`)

```python
class Arbiter:
    def __init__(self, producers: Sequence[Producer], reconciler: Reconciler):
        self.reconciler = reconciler
        self.by_parameter = _index(producers)      # ParameterId -> tuple[Producer, ...]

    async def project(self, selection):
        winners = {}                                 # ParameterId -> Producer
        for p in selection.parameters:
            for cand in self.reconciler.select(p, self.by_parameter.get(p, ())):
                if cand.node.capability.serves(p, selection.domain):
                    winners[p] = cand; break
        if not winners: raise CapabilityMismatch(...)

        by_producer = _group_by_producer(winners)    # Producer -> frozenset[ParameterId]
        if len(by_producer) == 1:                     # fast path: one node, Uniform passthrough
            producer, params = next(iter(by_producer.items()))
            return await producer.node.project(selection.with_params(params))
        return await self._assemble(by_producer, selection)   # >=2 nodes: PerParameter merge
```

`_index` maps each producer under `node.capability.parameters` through **one code path** — no
source-vs-calc branch. `capability` remains a `UnionCapability` over the producers' capabilities.

### 4.4 Multi-node assembly (`Arbiter._assemble`)

```python
async def _assemble(self, by_producer, selection):
    results = {producer: await producer.node.project(selection.with_params(params))
               for producer, params in by_producer.items()}    # each projected ONCE
    ranges, defs, prov = {}, {}, {}
    domain = None
    for producer, params in by_producer.items():
        cov = results[producer]
        domain = domain or cov.domain
        assert cov.domain == domain          # closed projection => every winner returns sel.domain
        for pid in params:
            ranges[pid] = cov.ranges[pid]
            defs[pid]   = cov.capability.parameters[pid]
            prov[pid]   = cov.provenance.summary(pid)   # each slice single-origin
    return CoverageRecord(
        capability=EnumerableCapability(domain=domain, parameters=defs),
        ranges=ranges,
        provenance=PerParameter(by_parameter=prov),
    )
```

This is the *record-building* half of the two combine axes (orthogonal parameters side by side, no
coverage-axis collision). The wind winner's `summary(wind_speed)` is the propagated Open-Meteo atomic
origin, so the assembled plane is `PerParameter` of single-origin `Provenance`s — no synthesis.

### 4.5 Calculator node (`nodes/calculator.py`) + kernel type (`nodes/catalog/calculators.py`)

```python
CombineFn = Callable[["Coverage"], tuple["EnumerableDomain", Mapping[ParameterId, "ParameterData"]]]

class Calculator:
    def __init__(self, outputs: Mapping[ParameterId, ParameterDef],
                 inputs: frozenset[ParameterId], fn: CombineFn, resolver: Manifold):
        self.outputs, self.inputs, self.fn, self.resolver = outputs, inputs, fn, resolver

    async def project(self, selection):
        ins = await self.resolver.project(Selection(selection.domain, self.inputs))  # D3
        domain, ranges = self.fn(ins)                       # kernel: structure only (D2)
        if ranges.keys() != self.outputs.keys():            # node: well-formedness
            raise RuntimeFailure(...)
        provenance = Uniform(ins.provenance.summary(next(iter(self.inputs))))  # propagate verbatim
        return CoverageRecord(
            capability=EnumerableCapability(domain=domain, parameters=dict(self.outputs)),
            ranges=ranges, provenance=provenance)          # node authors capability + provenance

    @property
    def capability(self):
        return DerivedCapability(self.outputs, self.inputs, self.resolver.capability)
```

Provenance note: both inputs are co-produced from one Open-Meteo fetch, so their origins are identical
and propagation of either is exact. A multi-origin `u/v` pair cannot arise in v1 (component sets share
one candidate list, ADR-0004); `SyntheticOrigin` stays an unexercised seam.

### 4.6 Wind kernel (new plugin module, e.g. `nodes/calculators/wind.py`)

```python
def _wind(cov: Coverage) -> tuple[EnumerableDomain, Mapping[ParameterId, ParameterData]]:
    u, v = cov.ranges[WIND_U], cov.ranges[WIND_V]
    present = _and_masks(u.present, v.present, n=len(cov.domain))   # elementwise AND
    speed = [math.hypot(a, b) for a, b in zip(u.values, v.values)]
    direction = [math.degrees(math.atan2(-a, -b)) % 360.0           # meteorological FROM-direction
                 for a, b in zip(u.values, v.values)]
    return cov.domain, {
        WIND_SPEED:     ParameterData(values=speed, present=present),
        WIND_DIRECTION: ParameterData(values=direction, present=present),
    }

MANIFEST = CalculatorManifest(fn_id="wind_uv", fn=_wind)   # no method tag: propagation, not synthesis
```

`atan2` sign convention must invert the `open_meteo._wind_component` encoding (`u = -speed·sinθ`,
`v = -speed·cosθ`) so `direction` round-trips to the vendor's meteorological degrees — a key test.
`wind_direction` is `circular`, but v1's nearest-neighbor read-back never interpolates it, so no angular
kernel is exercised.

### 4.7 Weaver Calculator weave (`nodes/weaver.py`)

Remove the `NotImplementedError` guard. Add memoized calculator construction:

```python
def weave(self, profile):
    source_producers = [Producer(Reservoir(self.stores.create(_source_grid(r)), r.provider),
                                 key) for key, r in profile.sources.sources.items()]
    reconciler = build_reconciler(profile.arbiter, profile.sources, profile.calculators)
    memo, visiting = {}, set()

    def producers_for(params):        # source + calc producers whose capability serves any param
        return [p for p in (source_producers + [build_calc(k) for k in profile.calculators.calculators])
                if params & p.node.capability.parameters.keys()]

    def build_calc(key):
        if key in memo: return memo[key]
        if key in visiting: raise CompositionError(f"calculator cycle at {key}")
        visiting.add(key)
        reg = profile.calculators.calculators[key]
        scoped = Arbiter(producers_for(reg.inputs), reconciler)          # inputs only => DAG
        calc = Calculator(reg.outputs, reg.inputs, reg.manifest.fn, scoped)
        node = Reservoir(self.stores.create(...), calc) if reg.stored else calc
        producer = Producer(node, key)
        visiting.discard(key); memo[key] = producer; return producer

    calc_producers = [build_calc(k) for k in profile.calculators.calculators]
    top = Arbiter(source_producers + calc_producers, reconciler)
    return Reservoir(self.stores.create(profile.root_store), top)
```

Memoization gives **one Calculator node per `CalculatorKey`**; both `wind_speed` and `wind_direction`
route to it, so requesting both together is a single winner. v1's wind calc is `stored=False` (no calc
store). (The `producers_for` sketch resolves calc producers lazily; the implementation will build the
memo once and read from it to avoid the double-walk shown above.)

## 5. Request-flow walkthrough (default `forecast_hourly`)

1. MCP edge builds `Selection(domain, {air_temperature, precipitation, relative_humidity, cloud_cover,
   wind_speed, wind_direction})` — `_EXPOSURE` already lists the two wind views and omits `wind_u/v`.
2. Best-view `Reservoir` → top `Arbiter.project`. Per parameter, `reconciler.select` orders candidates;
   canonical four admit to the Open-Meteo `Producer`; the two wind views admit to the wind `Calculator`
   `Producer`.
3. `by_producer` has **2 entries** (Open-Meteo, wind-calc) → `_assemble`:
   - Open-Meteo projected once for its four params → Coverage on `sel.domain` (`Uniform`).
   - Wind Calculator projected once for `{wind_speed, wind_direction}`:
     its scoped Arbiter resolves `{wind_u, wind_v}` — single Open-Meteo winner, `Uniform` Coverage — the
     kernel maps to speed/direction, the node stamps the **propagated** Open-Meteo origin.
   - Merge → one `CoverageRecord`, `PerParameter` provenance.
4. `serialize_coverage` iterates `capability.parameters` and reads `provenance.summary(pid)`; every
   origin is `AtomicOrigin` (Open-Meteo) → existing serializer passes unchanged.

Requesting **only** `{wind_speed, wind_direction}` → `by_producer` has 1 entry (the calc) → fast path,
single project, `Uniform`/propagated provenance. `wind_u` / `wind_v` are never requestable at the edge.

**Inner vs outer "sameness" (session 0012's unlocking distinction).** Two single-node claims must not
bleed together:

- **Inner — the Calculator resolving `(u, v)`:** single-node **by construction**. ADR-0004 co-production
  means a producer serves the whole component set from one origin or none, so `wind_u` and `wind_v`
  co-originate (both Open-Meteo in v1) and the scoped Arbiter **never merges** — its result is `Uniform`.
- **Outer — the top Arbiter assembling the response:** `wind_speed` (Calculator node) beside
  `air_temperature` (provider node) → disjoint winners → **the only genuine multi-node case in 002b**.
  The disjointness is **graph-structural, not data-origin**: all v1 data is Open-Meteo, yet the
  Calculator sits *beside* the provider under the top Arbiter, which assembles by **node identity**.

## 6. Implementation stages (TDD, red → green → refactor)

Each stage is a vertical slice that stays green at its boundary; write the failing test first.

- **S0 — Identity keys.** Add `CalculatorKey`, `ProducerKey`. Tests: `str` form, distinctness by
  `(method, name)`. Pure leaf, no behavior. *(green fast)*
- **S1 — Config + binder re-key.** `CalculatorSpec`→`CalculatorDef` (`outputs`, `priority`, `name?`);
  `RegisteredCalculator` gains `key`/`priority`/resolved `outputs`; `CalculatorRegistry` keyed by
  `CalculatorKey`; `CalculatorBinder.build(defs, parameters)` defaults name, derives key, resolves defs.
  Tests: key-keyed registry, resolved defs, name default, priority carried, unknown `fn_id` raises, two
  same-output/different-method → distinct keys. Update `test_weaver.test_nonempty_calculator_registry_*`
  fixture to the new shape.
- **S2 — Producer + Reconciler (sources only).** Add `Producer`, `Reconciler`/`PriorityReconciler`,
  `build_reconciler`; rewrite `Arbiter(producers, reconciler)` and Weaver to wrap source `Producer`s and
  build the reconciler. **Keep** the multi-node case raising temporarily (structural refactor only).
  Rewrite `test_arbiter` / `test_weaver` to the new constructors (`arbiter.by_parameter`,
  producer-based ranking). *(behaviorally green)*
- **S3 — Multi-node assembly.** Implement `_assemble` + `PerParameter`; retire the guard. Replace
  `test_different_winning_candidates_guard` with an assembly test (two fake single-param providers →
  merged Coverage, `PerParameter` provenance, one project each, shared domain). Integration-flavored.
- **S4 — Calculator node + wind kernel.** Change `CombineFn` (2b); `Calculator(outputs, inputs, fn,
  resolver)` with validate + propagate; `DerivedCapability(outputs, …)`; wind plugin module + `MANIFEST`.
  Tests: kernel math (`hypot`/`atan2` round-trip against `open_meteo._wind_component`, canonical units,
  present-mask AND), node propagation (output origin == input origin), `DerivedCapability.serves`.
- **S5 — Weaver calculator weave.** Memoized per-`CalculatorKey` build, scoped Arbiter over inputs,
  `stored?` wrap, cycle guard, add calc `Producer`s to the top list. Tests: both wind params → one node
  (memoization); scoped Arbiter admits only `wind_u/v` producers; acyclic; wind-beside-canonical hits
  `_assemble`.
- **S6 — Wire-up + e2e.** Register wind `MANIFEST` in `server.py::CALCULATOR_CATALOG`;
  `Settings.calculators()` emits the wind `CalculatorDef`. Mocked-transport integration test: default
  `forecast_hourly` returns canonical **and** `wind_speed`/`wind_direction` in one Coverage; derived
  params carry the Open-Meteo atomic origin/expiration; `wind_u`/`wind_v` rejected as not requestable.

## 7. Migration / compatibility / rollout

- **Internal refactor, additive surface.** The MCP response schema is unchanged; two new parameters
  appear in the default envelope. `serialize_coverage` already reads `provenance.summary(pid)` and
  asserts `AtomicOrigin`, so `PerParameter` + propagated origins need **no** serializer change.
- **No persisted state.** v1 wind calc is unstored; nothing to migrate in stores.
- **Rollout is config-gated.** With `CALCULATOR_CATALOG = {}` and `Settings.calculators() == ()`, the
  graph is behaviorally identical to today (the Weaver's calc branch is inert). S6 flips it on.
- **Test churn is front-loaded** in S2 (Arbiter/Weaver constructor changes ripple through
  `test_arbiter.py`, `test_weaver.py`). No production caller outside the woven graph constructs an
  `Arbiter` directly.

## 8. Failure handling & observability

- **Capability-based omission stays** (already in 002): a requested parameter that *no* producer serves
  is dropped from `winners` and simply absent; only an **empty** `winners` raises `CapabilityMismatch`.
- **Runtime-fault handling is NOT expanded here.** If Open-Meteo faults, the scoped Arbiter raises
  `RuntimeFailure`, the Calculator propagates it, and `_assemble`'s `await producer.node.project(...)`
  re-raises → the **whole request fails** (unchanged from today). Per-parameter **fault fall-through and
  partial success** — "omit any parameter whose candidates all fault, return the producible subset" — is
  ticket **009**, not 002b. In v1 the sole wind producer and the canonical producer are the *same*
  vendor, so an Open-Meteo outage fails the request regardless; 002b adds no graceful-degrade path.
- Kernel/well-formedness violations (ranges keys ≠ output group, length ≠ domain) are a
  build/derivation `RuntimeFailure`, authored by the node, never silent corruption.
- No new observability surface. Resolution logging/trace stays unassigned (concern #14 / roadmap).

## 9. Limitations & out-of-scope (by design)

- **No `SyntheticOrigin` in v1.** Lossless single-source propagation only; method-bearing / multi-origin
  derivation stays a declared seam.
- **No angular resampler.** `wind_direction` is `circular` but nearest-neighbor read-back never
  interpolates it (concern #5). A future kernel must go via u/v, never degree-average.
- **No domain-transforming kernel** yet — 2b keeps the seam open (`(domain, ranges)` return) but v1
  always returns `ins.domain`.
- **No calc store / single-flight.** `stored=False`; retention-by-wrapping is exercised later.
- **Scoped-input placement** stays Source-`Store`d (no top-store feedback edge) per ADR-0004.
- **Weaver co-production well-formedness assertion is deferred to 004** (session 0012). Asserting that a
  component set (`u`/`v`) shares one candidate list / order / footprint first earns its keep when a
  second provider exists; v1's single provider makes `u`/`v` co-originate trivially, so 002b does **not**
  build the assertion — a mismatched `(A.u, B.v)` pair cannot arise yet.

## 10. Follow-ups

**Doc alignment (this RFC changed accepted-doc contracts — docs done 2026-07-16; the code parts have
since landed in the build pass):**

- **F1 — ✅ ADR-0005 + [module-layout.md](../../module-layout.md):48:** `CalculatorBinder.build` now takes
  `parameters: ParameterTable`; `RegisteredCalculator` carries resolved output defs (D1). *(docs done)*
- **F2 — ✅ ADR-0004 (bullet + Calculator sketch):** kernel returns `(Domain, ranges)`, not `Coverage`;
  the node builds the Coverage + authors capability (D2). **Code landed (S4):** `calculators.py`
  `CombineFn` is `Callable[[Coverage], tuple[EnumerableDomain, Mapping[ParameterId, ParameterData]]]`.
- **F3 — ✅ ADR-0004 Calculator pseudocode:** `sel.with_params(self.inputs)` → `Selection(sel.domain,
  self.inputs)` (D3). *(docs done)*
- **F4 — ✅ [tickets/README.md](../../tickets/README.md):** the two stale "synthetic provenance" cells for
  002b now say propagated provider provenance + first multi-node assembly. **Code landed (S3):** the
  not-all-one-node guard and its `"005"` message are gone from `arbiter.py`. (005's ticket file was
  already reframed by session 0012 as provider-competition over this assembly.)
- **F5 — ✅ glossary `CalculatorKey`:** `name` binder-defaults to `"default"` (D-#3). *(docs done)*
- **F6 — ✅ ADR-0004 “Static / dynamic split” + [architecture.md](../../architecture.md) §Arbiter
  (+ data-flow step 4):** retargeted to `Arbiter(producers, reconciler)` / `build_reconciler` (align A1).
  *(docs done; code landed S2)*
- **F7 — ✅ Failure / partial-success ownership:** architecture §Failure and ADR-0004 Outcomes name
  per-parameter runtime-fault omission as the contract owned by
  [ticket 009](../../tickets/009-error-taxonomy-partial-success.md). Until 009, a `RuntimeFailure` fails the
  whole request (align A2; see §8). *(docs done)*

**Align decisions (2026-07-16 planning pass):** A1 = F6; A2 = F7; A3 = ticket 002 marked Done.

**Product/tech:**

- Resolution logging/trace ownership (concern #14) still unassigned.
- **Nodata masks are ticket 009, not 002b (already recorded).** 002 intentionally ships
  `present = None` (002 AC), so `open_meteo` decodes missing wind as `NaN` with `present=None`. The wind
  kernel therefore ANDs the input `present` masks **None-aware** (None = all-present), which in the 002
  era yields `present=None` — consistent with the canonical params. This is **forward-compatible**: when
  009 makes providers emit real `present[i]=False` masks and serialize nodata as `null`, the wind
  kernel inherits them through the AND with **zero rework**. 002b deliberately does **not** derive
  `present` from `NaN` (that would make wind more correct than its own inputs and duplicate 009).
