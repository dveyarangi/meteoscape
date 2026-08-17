# Edge — Provider surface

- **Status:** Normative

The seam record for the **Provider** surface: the boundary where Meteoscape meets an external weather
producer, and where the code that crosses it is authored.

**This edge points inward.** At [mcp](./mcp.md) and [embedding](./embedding.md) an outside caller
consumes Meteoscape; here Meteoscape consumes an outside producer, and the contract's consumer is the
**Provider author**. Read `Contract` as *what an author implements and may rely on*, and the two
`Invariants` groups as the two directions of the promise. A leaf has a second, outward face — the
vendor's HTTP API — with no contract of its own; what is stable there is Meteoscape's demand that the
leaf absorb the vendor's variability, which is why the **parity check** is one of this record's
validators rather than a separate surface — and for one promise below, the *only* one.

## Contract

### Implemented face

An author ships a **vendor `Probe`** plus a **catalogue face** — and, only when the producer's geometry
is one no existing shape covers, a wrapper too.

- **`Provider`** ([base.py](../../src/meteoscape/nodes/providers/base.py)) — `async project(Selection)
  -> Manifold`, `capability -> Capability`, `source_key -> SourceKey`. Stateless, no storage, no
  children. `capability`, cadence, and declared geometry are **members it publishes**, never arguments
  to `project` ([architecture §Provider](../architecture.md#provider-leaf-manifold)) — and those
  declarations are what resolve every request, so what exactly must be declared is
  [Resolution](#resolution--how-a-request-becomes-an-answer-geometry).
- **The shape wrapper** implements `Provider` for a family of producers that share a *geometric* shape
  — `TimelineProvider` for the point-plus-hourly-series family. It owns everything algebraic: both
  `ground` calls, `agreed_geometry`, unit verification, `decode`, Z grouping, capability construction,
  provenance stamping, the aligned crop, and the `ValueError → CapabilityMismatch` translation. A new
  producer of an existing shape adds **no** wrapper; a genuinely new geometry (gridded NWP, soundings —
  a [deferred seam](../../src/meteoscape/nodes/providers/timeline.py)) adds one.
  **Its constructor arguments are the per-offering facts** — the tap table, the native `step`, the
  `CadenceDef`, and the spatial reach (`longitudes` / `latitudes`, defaulting to whole-globe, which a
  regional producer overrides). v1 passes one offering's worth as leaf module constants, which is the
  honest state at one offering per provider; an offering-parameterized producer supplies a different row
  per `spec.name` rather than a different wrapper
  ([#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection), which also
  records what is still missing for that — a vendor model token in the query).
- **The vendor `Probe`** is what an author actually writes: a `Protocol`, injected, inheriting nothing
  (the [`Transport`](../../src/meteoscape/nodes/providers/base.py) precedent one layer down). Its face
  is shape-specific — `TimelineProbe.retrieve(longitude, latitude, over=window, variables=…) ->
  TimelineDelivery` — so the family prefix is load-bearing, not decorative. Note the point arrives as two
  **floats**, not a geometry: a Probe is handed coordinates it can put in a query string, never
  something it would have to narrow. It builds one vendor request and parses one
  response envelope. **It is not a Manifold and cannot be used as one**, which is the point of
  composition over an abstract base.
- **`TimelineDelivery`** — `valid_time: Sequence[datetime]`, `series` keyed by **vendor variable
  name** in **vendor units**, and `reported_units` when declared. Vendor-keyed rather than by
  `ParameterId` because the vendor↔parameter mapping is **many-to-many**: Open-Meteo's
  `wind_speed_10m` + `wind_direction_10m` jointly produce *both* `wind_u` and `wind_v`, so no
  parameter key is truthful before `decode` runs. The tap table owns that translation.
- **`TapTable`** — the declarations, and their execution: `engaged_by(parameters)` narrows to the taps
  a request touches, and the narrowed table answers `parameters`, `variables` (deduplicated — pinned by
  `test_wind_fetch_requests_shared_vendor_vars_once`), `by_level()` (the Z groups one native record
  each lands on), and `interpret`. It holds declarations and runs them; **anything needing a `Domain`
  belongs to the wrapper** — footprints included, since they are built from the tap table *together
  with* the wrapper's cadence, clock, reach, and `ParameterTable`.
- **Normalization has no object.** The role survives as *declaration plus generic machinery*: a leaf
  **declares** the tap table (vendor variables, expected unit tokens, `decode` functions) and the shape
  wrapper **executes** it. There is no `Normalizer` type to implement, and an author looking for one is
  looking for the tap table. Native geometry, never the request Domain
  ([architecture §Normalization](../architecture.md#normalization-vs-homogenization)).
- **`ProviderManifest`** ([catalog/providers.py](../../src/meteoscape/nodes/catalog/providers.py)) —
  `impl_id`, `provider_id`, `offerings` (`OfferingSpec`: exact parameter IDs + optional `StoreSpec`),
  `secret` slot, and the `build` face (`OfferingSpec, settings, secret_value, Clock, ParameterTable ->
  Provider`), optionally `expand`. The manifest is the plugin face; how catalogues are *filled* is
  [#26](../concerns.md#26-provider--calculator-plugin-scaffolding).
  **A declared `SecretSlot` is an optionality declaration, not just a name.** Absent value → the
  offering is never enabled and the server starts without it (graceful degrade is `Settings`' policy;
  the binder itself stays strict, so a def that *does* reach it must be complete). An author declaring
  a secret is therefore declaring the provider optional — and if a Calculator's only input came from it,
  that collision is [#35](../concerns.md#35-calculator-satisfiability-vs-optional-provider-degrade).
  **The seam is built and guarded, not prospective** — resolution, injection, and the dangling-ref
  failure are live in [composition.py](../../src/meteoscape/nodes/composition.py) and *validated by:*
  `test_secret_ref_reaches_build` / `test_dangling_secret_ref_raises`; Open-Meteo's `build` already
  receives `secret_value` and discards it as keyless. No shipped manifest yet declares a slot
  (`secret=None` today).
  `expand` — one manifest yielding several Providers — is likewise **unexercised**
  (`test_expand_name_none_not_implemented`); under the split it raises an unanswered question, several
  Probes behind one wrapper or several wrappers, which interacts with
  [#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection).
- **Two leaf shapes, not one.** The fetching leaf above is the common case; a producer whose data is
  **already materialized** declares an `EnumerableCapability` and wires **storeless** — its Source gets
  no `Store`, and configuring one is a build-time error (ADR-0006; *validated by:*
  `test_materialized_source_wires_storeless`, `test_store_configured_on_materialized_source_raises`).
  Whether such a producer has a `Probe` at all, or is a different `Provider` implementation entirely, is
  open at [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
- **Transport separation** — vendor I/O goes through the `Transport` seam so deterministic tests mock
  **HTTP**, never the Provider — **and never the `Probe`**, which composition makes mockable and this
  rule forbids: mocking it would skip the envelope parse that is the largest thing a Probe author can
  get wrong.

**The seam is typed by value, not by manifold.** A Probe may import, and nothing wider:

- **geometry and data value types** — `Interval`, `RegularAxis`, `ParameterData` (`manifold.domain`,
  `manifold.data`) and `ParameterId` (`parameters`);
- **its own shape's vocabulary** — `VendorVar`, `PointSeriesTap`, `TimelineDelivery`
  (`providers.timeline`);
- **the fetch seam** — `Transport`, `FetchRequest` (`providers.base`), which is how it reaches the
  vendor at all;
- **the error taxonomy** — `RuntimeFailure` (`errors`), which a Probe **must** raise on a malformed or
  unparseable envelope. `CapabilityMismatch` is *not* a Probe's to raise: whether a request is servable
  is decided by declared geometry, before the Probe is called.

It **never** imports the manifold types: `Domain`, `Selection`, `Coverage`, `Capability`,
`Provenance`, or `Clock`. Each exclusion buys an edge rule structurally rather than by trust — a Probe
handed a `Domain` would narrow it to recover a coordinate, re-importing the shape-versus-fault
misclassification the wrapper exists to delete; one that never sees a `Clock` **cannot** stamp
provenance wrong; one that never constructs a `Coverage` cannot mis-assemble one. Guardable the same
way reader independence is — an import-direction test — and listed as such below.

The shipped Provider's **evidence** has three pieces:

- **Reference reader** — `tests/parity/readers/<provider>.py`: fetches and parses the vendor's public
  response, converts to canonical units *independently*, returns a `ReferenceTimeline` plus raw
  evidence. Prefer a provider-maintained official client where it exposes the required semantics;
  otherwise a minimal direct fetch, with the suitability justification recorded in the check.
  **`ReferenceTimeline` is a deliberate structural twin of `TimelineDelivery` and must never be
  unified with it.** The two are a tick sequence plus named series apiece, and the temptation to share
  one dataclass is obvious and wrong: `parity.comparison` imports nothing from `meteoscape` precisely
  so readers stay guard-clean, and moving that type into `src/` would make every reader import
  Meteoscape and destroy the independence the whole check rests on. They are also twins of different
  *stages* — `ReferenceTimeline` is canonical-keyed and already converted, so its true counterpart is
  the wrapper's output, not the Probe's.
- **Live parity test** — `tests/parity/test_<provider>.py`: composes the real single-Provider root,
  drives it through the public protocol payload, declares per-parameter `ParitySpec`s, retries once
  with a **fresh** root, and on final failure writes the evidence bundle.
- **Deterministic coverage** — a `parse_reference` test over a canned vendor response under
  `tests/deterministic/`; the comparison engine itself is already covered.

Live parity is structurally outside the default suite — `testpaths` scopes `uv run pytest` to
`tests/deterministic/`, so live checks are explicit opt-in ([cicd.md](../cicd.md)):

```sh
uv run pytest tests/parity                  # all live parity checks
uv run pytest tests/parity -k open_meteo    # one provider
```

**Parity limits.** The reference reader consumes the same vendor API as the Provider, so a green
comparison verifies transport, units, and decoding, not semantic declarations shared by both sides.
Tick meaning and declared Z height therefore require deterministic guards against vendor
documentation → [#48](../concerns.md#48-a-tap-cannot-declare-where-its-value-sits-relative-to-the-tick).

### Request — what a leaf may be handed

A `Selection` (`Domain + parameters`) whose `domain` is typed the **base `Domain`**. The
representations a leaf sees today:

- **`GridDomain`** — a fully enumerable request; the leaf answers co-domained on it.
- **`SelectionDomain`** over `SelectableAxis = RegularAxis | VantageAxis | SnappedAxis` — the
  request-side representation, structurally `Separable`, never enumerable. A **`SnappedAxis`** carries
  bounds only — or none: the boundless member is **`ANY`**, axis-generic, and `ground` answers it
  with the producer's axis whole; the resolver's own grid supplies anchor and step (ADR-0002).

**Store-shaped asks.** The Source `Reservoir` asks the leaf with `ANY` on the axes its Holding spans
wholly (timeline: T and Z), so the leaf answers multi-domain in its native geometry. A cold request
fetches the provider's whole live window; later requests inside that fresh window read retained
Holdings. Read-back crops the served answer.

> **A leaf's declared live window is an estimate of what its vendor serves, not a promise.** The
> declared axis answers retention for itself — a rolling window satisfied once its horizon reaches
> the ask's start, a static one by containment
> ([ADR-0002](../adr/0002-data-model.md#the-two-predicates-admission-and-retention);
> [0119](../tickets/done/01-0119-live-window-edge-tolerance.md)). An ask the Holdings cannot meet is a
> `CapabilityMismatch`, not a refetch storm.
>
> **A leaf's cadence must therefore not exceed its `max_lead`**, or its Holding can fall entirely
> behind `now` between refreshes — enforced on `CadenceDef` construction, which raises `ValueError`:
> it holds both numbers and neither name (*validated by:* `test_cadence_must_not_exceed_max_lead` in
> [test_cadence.py](../../tests/deterministic/manifold/test_cadence.py)). When the cadence came from an
> **operator setting**, the leaf's `build` owes the translation — `CompositionError` naming its
> `SourceKey` and offering, `build` being the first layer that knows whose numbers these are —
> **⚠ unguarded**: no shipped leaf takes a cadence setting yet, so the first is
> [TWC](../tickets/01-0120-twc-provider.md) and the check lands with it.

- The **Reservoir's read-back** does the fact→product relabel: native Z cells (2 m, 10 m, surface,
  column) are rewritten onto the request's vantage; values and provenance untouched. The
  **`TODO (temporary)`** seam is owned by
  [0117](../tickets/done/01-0117-off-grid-homogenization.md). `agreed_geometry`'s single-answer law is
  deliberately **lifted on axes the request left `ANY`** — records differing there are exactly what
  boundlessness licenses.
- **The leaf's co-domained answer path is transitional in the composed graph.** Closure still
  requires it for any direct or enumerable ask, but the shipped wiring exercises the boundless
  branch at the Source.
- **The answer may carry the leaf's natural fetch unit** — wider than the ask's parameter set,
  never narrower. Open-Meteo's natural unit is its whole offering, which collapses the cold
  mixed-request double fetch; a leaf that answers narrow (per-variable billing) re-accepts that
  divergence for its own parameters —
  [#43](../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence). Today the
  whole tap table is the fetch unit, written once in the shape wrapper; a second Provider will test
  whether that economy fact belongs per offering.

**A leaf does not inspect request shape.** It **declares its geometry** — per-parameter footprints,
with a lattice-bearing axis wherever it can resolve a snapped member — and the request is resolved
against that declaration. Which shapes a leaf serves is therefore a **consequence of what it declares**,
  never a hand-written gate. A second Provider of this shape therefore contributes declarations,
  not another mode implementation.

### Resolution — how a request becomes an answer geometry

**One verb.** `ground(request: Domain, against: Domain) -> EnumerableDomain` is ADR-0001's
shape-correspondence sentence as a single operation: *the answer geometry `request` asks for, resolved
against `against`'s geometry.* A per-axis fold, dispatched by axis **kind**, never by mode:

- an **enumerable** member (a pinned `RegularAxis`, a vantage Z cell) passes through **by identity**;
- a **snapped** member takes what the answering axis clips itself to: the answering lattice keeps its
  own anchor and step, and the bounds decide only where it starts and stops — back to the tick whose
  *cell* contains the lower bound, forward to the last tick within the upper.

**The one axis operation underneath: `Axis.clip(bounds) -> Axis | None`, abstract on the base.** Each
axis kind answers for its own geometry — a lattice clips to a sub-lattice at its own phase, a single
cell survives whole or not at all, a span clips to a span, a clock-relative window materialises first
(the rolling case). `clip` returns whatever the restriction leaves; **needing cells is `ground`'s
requirement, not `clip`'s**, which is what makes *which modes a leaf serves* a reading of its own
declarations → [ADR-0002: snappable-to is a consequence, not a rule](../adr/0002-data-model.md).

Three properties an author depends on:

- **A leaf never dispatches on request type**, because `ground` did it: an exact request comes back
  unchanged — it is already its own answer — and *that identity is what collapses the mode branch*.
  Both modes take one code path.
- **It returns `EnumerableDomain`, and the wrapper narrows past it** — an author will see that and
  should not read it as a mistake. `EnumerableDomain` carries no `axis()`, so reading the resolved point
  and window, and handing the answer to `resample` (which crops `GridDomain` lattices only), both take
  the concrete type. Total in v1, since `GridDomain` is the only enumerable representation minted; this
  is where a second one would first have to be handled, and that is deliberately the *wrapper's* problem
  rather than a narrower `ground` signature → [ADR-0002: what ground
  returns](../adr/0002-data-model.md).
- **It raises `ValueError`, and the wrapper translates.** The algebra does not know *why* a resolution
  failed; the leaf does, and reports `CapabilityMismatch` at each call site. Two declines, and they say
  different things: *nothing survives the clip* (disjoint bounds — the raced-empty window pre-fetch, a
  foreign window post-fetch, and a snapped **X/Y**, which is temporal-by-type meeting a spatial axis)
  and *the answering axis has no cells* (a leaf declaring T as a plain span rather than a lattice).

**A second verb: `agreed_geometry`.** One `project` answers with **one** geometry (ADR-0001), so a fold
over several grounded resolutions either returns the geometry they agree on or raises. It lives beside
`ground`, not in any leaf — the law binds every producer that folds records.

**The rule has exactly one exception, and the fold still answers once.** That axes the request **pins
or snaps** must ground identically is permanent. An axis left **`ANY`** is the sole licence for
resolutions to differ: the fold validates that difference and returns the geometry authoritative on
every bounded axis, which is all any caller reads. It does **not** return the differing members,
because nothing consumes them as a value — records carry their own domains, and the **multi-domain
carrier** is built from the records themselves. The licence is derived from the request, never asserted
by a caller.

The fold is **`agreed_geometry`**, the carrier is **`CoverageSet`**, and `ANY` is the **boundless
snapped member** (`interval=None`). `SelectableAxis` gains no new kind; the licence keys on
boundlessness inside the fold.

**Two call sites, and what each grounds against.** The wrapper calls `ground` once before the vendor
call and once after — never in between, and never anywhere else. Both ends are plural, so both fold:

```python
async def project(self, selection: Selection) -> Manifold:
    if not selection.parameters or selection.parameters - self._taps.parameters:
        raise CapabilityMismatch(...)                                               # settled before the wire
    boundless = open_axes(selection.domain)                                         # what the ask left to me
    taps   = self._taps if boundless else self._taps.engaged_by(selection.parameters)
    wanted = agreed_geometry((ground(selection.domain, fp) for fp in footprints(taps)),
                             request=selection.domain)                              # …against what I declare
    (lon, lat), window = point_of(wanted), window_of(wanted)

    delivery = await self._probe.retrieve(longitude=lon, latitude=lat, over=window,
                                          variables=taps.variables)

    records = interpret(delivery, taps, at=(lon, lat), stamped=self._stamp())       # units, decode, Z groups
    answer  = agreed_geometry((ground(selection.domain, r.domain) for r in records),
                              request=selection.domain)                             # …against what arrived
    group   = CoverageSet(records)
    return group if boundless else await group.project(Selection(answer, selection.parameters))
```

**The parameter facet declines exactly once, and before the wire:** an ask naming nothing this leaf
serves, or naming something it does not, is `CapabilityMismatch` with no fetch attempted. That is what
leaves the carrier's own unheld-parameter arm unreachable from here, so no guard downstream repeats it.

**The last line is the whole of the answer discipline.** With no open axis the answer is cropped to
exactly what was asked. With one, the crop is skipped on **both** facets at once — native cells stay
(Z per record) and the **whole fetch unit** rides along — because a crop to the request's geometry and
a crop to its parameter set are the same eager fold on two facets, and the boundless axis licenses
both. What returns is then the carrier, not a `Coverage`: a caller must not assume a single `domain`.

Pre-fetch the fold runs over the leaf's **per-parameter footprints** (they differ in Z); post-fetch over
the **native records** (grouped by Z). Neither *raises* on Z: a request that pins or apertures Z grounds
it by identity, so every footprint yields the same answer geometry, while one that leaves Z open makes
them differ deliberately and the fold validates the licence instead.

**Be precise about which fold can actually fire, because the two are not symmetric.** The *pre-fetch*
fold is live: a leaf declaring **different reaches per parameter** grounds its footprints to different
answers, which is the limitation stated below. The *post-fetch* fold's **raising** arm is a law
statement, **structurally unfirable in this shape** — one delivery yields one tick lattice, stamped
onto every record, and on a bounded axis Z grounds by identity, so the records cannot disagree there.
Its **validating** arm is live and exercised: it runs on every ask that leaves an axis open, which is
how the differing native Z cells reach the carrier. The raising arm is kept because the law binds every
producer that folds records, including a future shape that derives a lattice **per record**; it is not
kept as a runtime guard, and no test can pin it through `project`. In particular it does **not** catch a vendor
answering the two fetches of one request differently: those are two separate `project` calls, and the
`RuntimeFailure` that catches them is the **Arbiter's** closed-projection check (see the invariant on
per-winner projection, and `test_winner_domains_that_differ_fail_the_whole_request` in
[test_arbiter.py](../../tests/deterministic/nodes/test_arbiter.py)).

**That second case is a real limitation, so state it rather than let it be discovered:** a leaf **cannot
serve, in one call, two parameters whose declared reaches differ on a **bounded** snapped axis.** A
vendor offering 16 days of temperature but 5 of precipitation refuses a mixed snapped request with
`CapabilityMismatch` rather than answering multi-domain. That is correct under closure: the licence for
a multi-domain answer is **boundlessness**, so bounds a requester states are answered identically or
not at all. An ask that leaves the axis open — the retentive store's refill shape — licenses the
difference instead; what stays refused is specifically a request that *states* the bounds. Live driver:
[#20](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection).

**The tick lattice is derived, never taken on the Probe's word.** `interpret` builds it from the
delivered `valid_time` and checks it against the **declared** step — which is what turns *declared
geometry matches delivery* from a promise into a computation, and catches a mis-declared provider
deterministically instead of only at parity.

**What the leaf must therefore *not* contain.** This is the load-bearing half of the law: no `floor_to`
or step arithmetic, no clamp to the live window, no end-inclusivity handling, no raced-empty guard, no
index math, no clock anywhere in the Probe, and no branch on request mode. Every one of those is
`clip` against the declared lattice — the lattice **is** the window — and writing any of them by hand
re-derives the mode inside the leaf, which is exactly what the second Provider must not have to do.

**What the leaf must therefore declare**, for any of it to work:

- **Per-parameter footprints** at the leaf's own geometry — static spatial and Z bounds, and a
  clock-relative T axis whose `CadenceDef` declares the availability base; without a
  Shelf it follows the run → [ADR-0003: cadence](../adr/0003-provenance-and-origin.md#run-identity-fetch-buckets-and-freshness--the-cadence).
- **An axis that clips to cells wherever the leaf can resolve a snapped member.** For a rolling T that
  is `RollingAxis.clip`, which materialises the live window into the lattice its series actually
  arrives on before restricting it. A leaf that declares such an axis serves snapped requests on it;
  one that declares a span is declined **by the algebra reading that declaration** — no leaf writes
  that rejection.
- **Its native series step** — how densely one run samples time, which is **not** the cadence
  (`CadenceDef` times *runs*; a 6-hourly run may publish an hourly series). It is declared with the
  provider shape and is **required, not optional**, precisely so a rolling axis never invents a lattice
  it does not have: a leaf whose series is genuinely irregular declares a different T axis and is
  declined honestly.

**The two clock reads are by design.** A snapped request reads the clock once when the leaf grounds
pre-fetch (inside the rolling axis's availability `extent`) and once after the fetch to stamp run
provenance. They share a `Clock`, not necessarily an anchor. The answer is clipped to the **requested
bounds**, never to the racy window, so a window that rolls between them at worst trims the answer —
except the raced-empty case, where the clip finds no overlap and the leaf declines pre-fetch, without
a vendor call.

### Response — what a leaf returns

**A leaf answers on the geometry it was asked.** Closure is not relaxed for leaves: *"`project(sel)`
must return a Coverage on `sel.domain`"* ([ADR-0001](../adr/0001-manifold-algebra-and-composition.md)),
and architecture states it for this node specifically — *"asked a fully enumerable Selection it samples
to one co-domained `Coverage`, **like any Manifold**"*, with
[§Reservoir](../architecture.md#reservoir) adding the parenthetical that settles it: **homogenization
is *not* leaf-only**. What *is* leaf-forbidden is **normalization** emitting on the request Domain — a
claim about a different step, and one easy to over-read: the tap table produces canonical values at the
vendor's own geometry, and only the crop afterwards lands them on the answer's.

**At what strength.** Three exist; the leaf owns the middle one:

- *Identity-or-fail* — the delivered geometry must already equal the request positionally. The leaf
  used to do this (a length check, then passthrough) and it was **under-implementation, not the
  contract**: it refuses requests that are perfectly croppable, which contradicts closure. Gone at m4.
- **Aligned crop — the leaf's promise.** Same step, on-phase anchor, differing extent; index arithmetic
  only, no interpolation. [`resample`](../../src/meteoscape/manifold/sampling.py) implements exactly
  this and the wrapper hands every answer through it — which also retired the hand-written length
  assertion in favour of a check by the component that owns index math, **reported rather than
  asserted** ([#31](../concerns.md#31-positional-alignment-is-asserted-never-checked), re-aimed at the
  answer). A crop onto a geometry the vendor already delivered exactly is an equality that holds and a
  no-op, which is how both request modes take one path.
- *Resamplers* — off-grid points, differing steps, coarser-grid re-aggregation. **Not the leaf's.**
  `resample` refuses these by name ("requires Reservoir homogenization"); they belong to
  [#5](../concerns.md#5-read-time-homogenization-fidelity) and
  [#15](../concerns.md#15-coarser-grid-resampling-and-aggregation-semantics).

So: off-phase, differing-step, and off-grid asks are `CapabilityMismatch` from the leaf and the
Reservoir's to serve — with [#21](../concerns.md#21-serves-extent-vs-project-crop-ability) owning the
crop-ability gap.

**What the answer carries**, whichever geometry it lands on:

- **Native records**: `Coverage`s at the producer's **own** geometry, grouped by shared native Domain —
  reaching the store un-flattened (ADR-0006). This is what *normalization* produces and what a Store
  retains as identity; it is the intermediate, not the answer, until `ANY` makes it both.
- **Canonical units**, converted by the wrapper from the Probe's vendor-unit delivery
  ([parameters.md](../parameters.md)); vendor-native units never escape the wrapper.
- **Full Provider-authored provenance**, stamped at fetch: a single-fetch `Uniform` plane carrying the
  run `issue_time` from the leaf's cadence anchor and an `expiration` derived from that cadence
  (ADR-0003).
- **Vendor looseness is trimmed, not rejected — on a snapped ask.** A vendor answering wider than the
  bounds is cropped, and one answering *shorter* is an **honest shorter answer**, not garbage: the
  answer geometry is grounded against **what arrived**, so a short delivery simply grounds shorter and
  there is nothing to fall short of.
  **Against an *exact* ask the same shortness is a fault**, and the asymmetry is the whole point of the
  two modes: an enumerable request names coordinates the leaf owes under closure, so a delivery ending
  before them leaves a crop that is aligned but **short by a known count** — a `Shortfall`, translated
  to `RuntimeFailure` ("delivered less than it declared"). That is the caller's own geometry going
  unanswered, not vendor looseness. Interim: when
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback) pads that tail as
  `present=False`, the count is what padding consumes and the failure goes away.

**Which Z the answer may land on, and what that relabel claims.** The crop treats the two Z request
shapes differently, and the difference is a promise, not an implementation accident:

```
native 2 m point  →  vantage [0,10]   identity crop: one cell onto one cell — relabels
native 2 m point  →  pinned  10 m     lattice-to-lattice: no aligned offset — refused
```

A **vantage** cell is an aperture, so landing a native level in it is the fact→product step and it is
honest exactly because admission already gated that parameter against its own native footprint. A
**pinned** Z names a coordinate the caller owns, so a record measured elsewhere cannot answer it and
the alignment read declines rather than mis-indexing. Before the carrier, a mixed-parameter ask
pinning Z was answered by stacking every record on the first one's cells, which silently reported 10 m
wind at a 2 m pin; each parameter now crops against its **own** record.

What the relabel claims is an **∃-claim** — *measured somewhere in `[0,10]`* — never a ∀-claim about
every level in it. So the label may not later be narrowed by plain inclusion: `[0,5]` does not follow
from `[0,10]`, because the sample may have sat at eight metres. Same rule, second site: the store's
version of it is [#25](../concerns.md#25-root-store-holding-reuse-across-vantage-windows).

### Outcomes

The leaf raises from the shared taxonomy
([architecture §Failure](../architecture.md#failure-nodata-and-availability)):

- **`CapabilityMismatch`** — a request this leaf cannot serve: a shape it does not resolve (a snapped
  member against an axis that clips to no cells), nothing left after clipping to the live window (including the
  raced-empty case), or requested footprints / delivered records that resolve to different geometries.
  Pre-fetch wherever the fact is knowable pre-fetch — a decline must not cost a vendor call.
- **`RuntimeFailure`** — an upstream fault or vendor garbage: 5xx, timeout, transport error, non-JSON
  body, an unparseable envelope, an empty series, a unit report contradicting the declaration (or absent
  where the Probe declared it would be there), a series **off the declared step** or gapped, keys the
  Probe was not asked for, array-length disagreement, and a delivery **falling short of an exact
  request's own coordinates**. **Never** a request the leaf merely cannot serve.
- **`BadRequest`** is not a leaf's to raise — it belongs to the surface that parsed the caller's input.

**A fourth outcome exists and is deliberately outside the taxonomy: the engine's own assert.** The
sampler raises `NotImplementedError` for a crop index arithmetic cannot express — off-phase, or a
different step. It reads like a leak and is not one: it means **`serves` admitted a request `project`
cannot answer**, so it is an internal assert that admission over-promised, and
[#21](../concerns.md#21-serves-extent-vs-project-crop-ability) closes it *inside `serves`* rather than
by translating it here. The translation is what must not happen — folding it into
`CapabilityMismatch` would say *"nothing here serves that"* about data the leaf is holding, collapsing
a fact about the **looker** into a fact about the **world**. Those two refusals are the ones
[#36](../concerns.md#36-unserved-and-uncomparable-are-indistinguishable) exists to keep apart, and the
distinction is only recoverable at the moment of refusal. So: never caught, never re-categorised, and
never pinned by a test as expected refusal behaviour.

### Vendor-face obligations

The leaf's outward face has no contract Meteoscape can state, so it states the author's obligations:
bounded requests; the vendor's credentials, quotas, attribution, and terms of use respected; secrets
never exposed in fixtures, logs, or failure artifacts; and the vendor's model-run boundary absorbed
rather than fought (a run publishing between two reads is a legitimate mismatch, not a defect).

## Invariants

### What the engine guarantees a leaf

- A `Selection` always carries **exactly the four axes**, each keyed by its own name — *validated by:*
  `_validate_four_axes` in [domain.py](../../src/meteoscape/manifold/domain.py),
  [test_domain.py](../../tests/deterministic/manifold/test_domain.py).
- `build` runs **once at composition** with an injected `Clock` and `ParameterTable`; the clock is never
  threaded through `project`, so a rolling declaration reads it where ADR-0003 put it — *validated by:*
  `test_one_offering_binds_to_registry` / `test_secret_ref_reaches_build` in
  [test_composition.py](../../tests/deterministic/nodes/test_composition.py),
  `test_provenance_authored_from_cadence_and_clock` in
  [test_open_meteo.py](../../tests/deterministic/nodes/providers/test_open_meteo.py).
- On the Arbiter path a leaf is reached **only after `serves` admitted the request**, so a leaf's own
  shape declines guard direct callers rather than the normal path — *validated by:*
  [test_arbiter.py](../../tests/deterministic/nodes/test_arbiter.py).
- A leaf's `Capability` is **forwarded unchanged** by its Source; retention adds no capability and the
  store grid is a fidelity floor, not a boundary, so a leaf declares its reach once and it survives to
  the root — *validated by:* `test_single_source_weaves_capability_and_stores` in
  [test_weaver.py](../../tests/deterministic/nodes/test_weaver.py),
  [Reservoir.capability](../../src/meteoscape/nodes/reservoir.py).
- **A leaf is projected once per *winner*, not once per request** — but **how often that reaches the
  vendor is retention's business, not the leaf's.** A request mixing direct and derived Parameters
  resolves through two winners, but Open-Meteo's natural fetch unit warms the shared Source: a cold
  mixed request costs one vendor trip and a warm repeat none. A narrow-answering Provider may instead
  cost one trip per winner
  ([#43](../concerns.md#43-narrow-answering-providers-re-open-mixed-request-run-divergence)).
  *Validated by:* `test_forecast_hourly_e2e_and_refetch` (`route.call_count == 1` across two
  requests) and `test_snapped_mixed_request_shares_one_vendor_geometry` in
  [test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py).
  If separate winner fetches deliver different T geometries, the Arbiter's closed-projection check
  fails the whole request with `RuntimeFailure`; the leaf must not compensate for that fold-level
  invariant. *Validated by:*
  `test_winner_domains_that_differ_fail_the_whole_request` in
  [test_arbiter.py](../../tests/deterministic/nodes/test_arbiter.py).

### What every leaf must uphold

- **A leaf serves the modes its declarations imply, and writes no mode code.** A snapped ask is answered
  on the leaf's own lattice within the bounds — mid-hour bounds floored onto its ticks before any vendor
  call, a wider delivery trimmed, a disjoint one declined — with no branch on request shape anywhere in
  the leaf and no snap arithmetic outside `RegularAxis.clip` — *validated by:*
  `test_snapped_bounds_inside_window_map_to_floored_hours`,
  `test_snapped_mid_hour_bounds_floor_both_edges`,
  `test_snapped_bounds_straddling_window_clamp_to_window`,
  `test_snapped_wider_vendor_response_is_trimmed`, `test_snapped_shorter_vendor_response_is_honest`,
  `test_enumerable_t_in_a_selection_domain_is_served` in
  [test_open_meteo.py](../../tests/deterministic/nodes/providers/test_open_meteo.py), and end to end
  through the woven profile by `test_snapped_selection_resolves_through_the_woven_profile` in
  [test_e2e_forecast.py](../../tests/deterministic/test_e2e_forecast.py).
- **Canonical units at the leaf** — vendor-native units are converted before anything downstream sees
  them (Open-Meteo `km/h → m/s`) — *validated by:* `test_unit_mismatch_raises_runtime_failure` in
  [test_open_meteo.py](../../tests/deterministic/nodes/providers/test_open_meteo.py), live
  [parity check](../../tests/parity/test_open_meteo.py).
  **Evidence strength is per-provider, and the record says which.** A Probe that **declares
  `reports_units`** has its claim checked against the tap table's expected tokens on every call, and a
  Probe that declares it but returns no report is a `RuntimeFailure` — the declaration is verified, not
  trusted. A producer that publishes no units in its payload declares nothing, and for it this invariant
  is **parity-verified only**: the reference reader converts independently, so the live check is the
  sole guard. Making such a Probe echo the *declared* units back would be a fabricated confirmation —
  the check would pass by construction. This is a live reading of
  [#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted): for those providers the
  unenforced, unrouted check is the only one there is. Today's single provider declares `reports_units`
  and is checked on every call.
- **A `Probe` touches no manifold types** — it speaks `Interval`, `RegularAxis`, `ParameterData`,
  `ParameterId`, and `VendorVar`, and never `Domain`, `Selection`, `Coverage`, `Capability`,
  `Provenance`, or `Clock`. Each exclusion removes a way to be wrong rather than warning against it —
  *validated by:* [test_probe_seam_guard.py](../../tests/deterministic/test_probe_seam_guard.py), a
  static check over every vendor module that is not a shared one, so a **new** vendor file is guarded
  the moment it exists. Two rules, because the module is not only its Probe: the manifold types are
  never imported at all, and no `*Probe` class body references any of them — including `Clock`, which
  the catalogue's `build` face may hold and hand to the wrapper but the Probe may never see.
- **Vendor nulls survive as nodata**, never as `NaN` and never fabricated — *validated by:*
  `test_vendor_null_serializes_as_json_null`, `test_null_wind_speed_marks_both_components_absent`.
- **Provenance is authored at fetch**, per parameter, with origin and expiration derived from the leaf's
  own cadence — *validated by:* `test_provenance_authored_from_cadence_and_clock`.
- **`source_key` is producer identity and nothing else** — `(provider_id, dataset)`, stamped onto atomic
  provenance, **never** carrying priority (ranking is the reconciler's), and **unique across enabled
  offerings**: two offerings colliding on one key is a build-time failure, not a runtime surprise —
  *validated by:* `test_duplicate_source_key_raises` in
  [test_composition.py](../../tests/deterministic/nodes/test_composition.py),
  [test_identity.py](../../tests/deterministic/test_identity.py).
- **Native records carry native geometry**, grouped by shared Domain — *validated by:*
  `test_taps_group_into_four_native_levels`, `test_interpret_converts_and_decodes_every_served_parameter`,
  `test_capability_declares_six_native_z_facts`.
- **Declared geometry matches what the vendor actually delivers.** The wrapper derives the tick lattice
  from the delivered stamps and holds it against the **declared** step, so a leaf whose series lands off
  its own declaration fails **loudly** rather than grounding to one lattice and being indexed on another
  — the honest failure for a mis-declared provider — *validated by:*
  `test_series_off_the_declared_step_is_a_vendor_fault` in
  [test_open_meteo.py](../../tests/deterministic/nodes/providers/test_open_meteo.py), and the live
  [parity check](../../tests/parity/test_open_meteo.py) (the only place declaration and delivery are
  compared against **reality**).
- **Records folded into one answer must agree** on every axis the request pins or snaps: one `project`
  answers with one geometry (ADR-0001), and the only licence for multi-domain is an axis the request
  left entirely to the producer — *validated by:* `test_agreed_geometry_folds_resolutions_that_agree` in
  [test_domain.py](../../tests/deterministic/manifold/test_domain.py), where the law lives.
  **Deliberately unvalidated at this edge, and not a gap:** the timeline shape stamps one derived
  lattice onto every record of a delivery, so its records *cannot* disagree — the post-fetch fold is
  unfirable by construction (see [Resolution](#resolution--how-a-request-becomes-an-answer-geometry)).
  A shape that derives a lattice per record owes the pin the timeline shape cannot carry.
- **Unservable is `CapabilityMismatch`, upstream fault is `RuntimeFailure`**, and a decline costs no
  vendor call — *validated by:* `test_snapped_raced_empty_raises_without_vendor_call`,
  `test_snapped_non_t_axis_raises_without_vendor_call`,
  `test_snapped_disjoint_vendor_window_is_mismatch`,
  `test_httpx_transport_5xx_is_runtime_failure` and siblings.
- **A reference reader imports no Meteoscape code** — not the Provider, its shape wrapper, its taps, or
  conversion helpers, and nothing transitively reaching them — *validated by:*
  [test_parity_reader_guard.py](../../tests/deterministic/test_parity_reader_guard.py), which guards
  every module in `readers/` with no registration.
- **Parity compares at the public protocol payload**, never engine internals — so the comparison judges
  the whole composed path including serialization, where unit labels, nodata-as-`null`, and time
  formatting live. Raw vendor responses are failure *evidence* only, never the comparison target —
  *validated by:* [test_open_meteo.py](../../tests/parity/test_open_meteo.py) (drives the in-process
  MCP client).
- **Comparison semantics are declared, not implied** — exact equality for lossless pass-through,
  justified tolerances for conversions, circular distance for direction, matching nodata positions; and
  where the engine withholds a value under a defined condition (`wind_direction` below the calm floor)
  the check adopts the engine's **own named constant**, never a reinvented threshold that can drift —
  *validated by:* `ParitySpec` declarations in
  [test_open_meteo.py](../../tests/parity/test_open_meteo.py),
  [test_parity_comparison.py](../../tests/deterministic/test_parity_comparison.py).
## Concerns

- [#26 — Provider / calculator plugin scaffolding](../concerns.md#26-provider--calculator-plugin-scaffolding)
  — this edge's central open question, the analogue of #39 at the embedding surface: the implemented
  face is settled, its **packaging** is not. Built-in vs optional partitioning, where filled catalogues
  live, entry-point discovery vs install extras. It decides when "author" stops meaning "us".
  **Scope note:** #26 covers provider *and calculator* scaffolding; this record covers only the
  provider half. Calculator authoring is a distinct surface (no vendor face, no parity check, no tap
  table, no fetch-time provenance) and would earn its own record if it ever needs one — it is
  deliberately absent here, not overlooked.
- [#41 — Parity evidence is unenforced and unrouted](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted)
  — parity is strong evidence for the shipped Provider, but nothing yet requires or routes a parity
  check when a new manifest is added. The enforcement rule remains Roadmap, not a live invariant.
- [#23 — Spatial vs temporal `RegularAxis` types](../concerns.md#23-spatial-vs-temporal-regularaxis-types)
  — **inverts the embedding reading.** There the split must stay *invisible* to request authors; here it
  is visible and wanted, because it is what turns coordinate-kind `isinstance` checks into static ones.
  m4 adds **no** such narrowing — `RegularAxis.clip` is one coordinate-generic expression — so what a
  spatial sibling would buy here is a float phase-tolerance policy stated statically rather than
  chosen per call; recorded at #23, not decided here.
- [#18 — Clock-anchored footprint fidelity](../concerns.md#18-clock-anchored-footprint-fidelity)
  — static declaration versus vendor-real availability; over-promising surfaces here as edge nodata.
- [#20 — Provider multi-resolution offerings](../concerns.md#20-provider-multi-resolution-offerings-offering-aware-selection)
  — `OfferingSpec` is a manifest concept, so a provider exposing several resolutions grows this edge's
  face first.
- [#37 — Storeless materialized producers](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization)
  — a leaf whose data is already materialized declares an `EnumerableCapability` and wires storeless: a
  second legitimate leaf shape this Contract must not accidentally exclude.
- [#12 — Curvilinear domains](../concerns.md#12-curvilinear-domains) — the **source role**: a leaf
  declaring non-separable geometry advertises through the same `Capability` field, and today fails
  composition rather than the request path.
- [#10 — Parameter conventions](../concerns.md#10-parameter-conventions) — canonical units are converted
  *at the leaf*, so the lossless-vs-degrading conversion-quality signal surfaces here first
  ([010](../tickets/01-0122-unit-conversion-edge.md)).

## Roadmap

1. **A second Provider** — the first real test of *declaration, not gate*: **TWC** ships a
   `TimelineProbe`, not a leaf (its hourly forecast API is the same point-plus-series shape, so no wrapper),
   inheriting snapped resolution by declaring its own geometry. Also the first shipped manifest to
   declare a `SecretSlot` and, likely, the first exercise of the non-self-reporting units path —
   [011](../tickets/01-0120-twc-provider.md). The **fallback behaviour** it enables is a
   separate ticket, [004](../tickets/01-0121-second-provider-fallback.md), and lands at the
   [MCP edge](./mcp.md).
2. **Parity coverage becomes enforced and routed** — a guard connecting a manifest to its check, and
   selection that does not depend on branch names —
   [#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted); no owning ticket.
3. **A second provider *shape*** — gridded NWP or soundings, the first case that adds a wrapper rather
   than a Probe ([timeline.py](../../src/meteoscape/nodes/providers/timeline.py) names it a deferred
   seam); no owning ticket.
4. **Third-party plugin authoring** — the point at which this edge's audience leaves the repository —
   [#26](../concerns.md#26-provider--calculator-plugin-scaffolding); no owning ticket.
