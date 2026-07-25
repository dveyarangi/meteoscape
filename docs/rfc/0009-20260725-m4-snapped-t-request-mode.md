# RFC 0009 · 2026-07-25 · m4 — Snapped-T request mode: implementation plan

Implementation plan for [m4](../tickets/m4-snapped-t-request-mode.md), whose design was settled at
the 2026-07-25 align (recorded in the ticket; ADR-0002 already amended — Snapped is **bounds-only**:
the request fixes bounds, the resolver's grid supplies anchor *and* step,
`snapped → exact = anchor(grid) ⊕ step(grid) ⊕ bounds(request)`).

**Scope in one line:** two new request-side types in `domain.py` (`SnappedAxis`,
`SelectionDomain` over a `SelectableAxis` union) and one branch in the Open-Meteo leaf (fetch
bounds = `bounds ∩ live window`; answer lattice derived from the vendor response under coherence
validation) — zero changes to `Selection`, `Capability`, `Arbiter`, `Reservoir`, sampling, Gateway,
or the MCP edge.

## Boundaries involved

| Boundary | Owner | What m4 does to it |
|---|---|---|
| `Domain` / axis surface (`manifold/domain.py`) | [ADR-0002](../adr/0002-data-model.md) | Adds `SnappedAxis`, `SelectableAxis`, `SelectionDomain`. No existing type changes. |
| Admission (`Capability.serves` → per-axis `matches`) | [ADR-0004](../adr/0004-producer-resolution-and-capability.md) | **No code change** — `SnappedAxis.matches` (intersection) rides the existing request-side per-axis gate, exactly the `VantageAxis` precedent. Pinned by tests. |
| Arbiter | ADR-0004 | **Untouched.** Single winner, wholesale (#13 scoped position). |
| Open-Meteo leaf (`nodes/providers/open_meteo.py`) | [provider-authoring](../provider-authoring.md) | `_forecast_request` and `_assemble` gain a `SelectionDomain` branch; the enumerable `GridDomain` path is byte-for-byte unchanged. |
| Reservoir | [architecture §Reservoir](../architecture.md#reservoir) | **Untouched** (pass-through pre-006). |
| MCP edge (`api/mcp_app.py`), Gateway | [architecture §Contract surfaces](../architecture.md#contract-surfaces) | **Untouched** — m4 is product-invisible; the edge migrates to `SelectionDomain` at 003c. |
| Sampling engine (`manifold/sampling.py`) | ADR-0002 | **Untouched.** v1 wiring never routes a snapped Selection to `resample` (no store; the leaf serves). Its non-enumerable guard message stays as-is. |

## Facts that shape the implementation (verified 2026-07-25)

1. **Admission needs no new code.** `FootprintCapability.serves` calls
   `footprint.matches(requested)`; `FootprintDomain.matches` requires the *request* to be
   `Separable` (structural, `runtime_checkable`) and folds `requested.axis(n).matches(declared)`
   per axis (`domain.py`). `SelectionDomain` exposing `axis()` is therefore admissible the moment
   it exists, and `SnappedAxis.matches` = intersection is the whole mode-dependence. `Interval`
   comparisons are boundary-inclusive (`<=` both ways in `contains`/`intersects`), so a request
   touching the window edge admits and yields a single tick.
2. **`Selection.domain` is already typed base `Domain`** (`manifold/core.py`) — no `Selection`
   change; internal store-shaped `GridDomain` Selections stay legal forever (ADR-0002 as amended).
3. **The normalizer already validates hourly regularity and array lengths**
   (`OpenMeteoNormalizer.normalize`: `tick != times[0] + HOURLY_STEP * i` → `RuntimeFailure`;
   per-var length checks). The snapped coherence check adds only: records share one T axis, first
   tick ≥ `floor_to(bounds.lower, HOURLY_STEP)`, last tick ≤ `bounds.upper`.
4. **The leaf's T lattice is epoch-hour-aligned by construction**: `CadenceDef.anchor` uses
   `floor_to(·, cadence)` with Δ = 1 h and `max_lead` = 16 d, so `window.lower` and
   `window.upper` are whole hours, and `floor_to(·, HOURLY_STEP)` on request bounds lands on the
   same lattice. No foreign-anchor case exists for this provider.
5. **Two clock reads in the snapped path are benign by design**: one at request-build (fetch
   bounds) and the existing post-fetch read (provenance). The vendor is the authority on what
   exists; coherence validates against the *requested bounds* (fixed), never the racy window. A
   window that rolls between admission and fetch at worst trims the answer — except the
   raced-empty case, which has its own guard (below).
6. **All existing `GridDomain` construction sites keep working**: the edge (`build_selection`),
   fakes (`sample_lattice`, `point_timeline_domain`), and the normalizer build `GridDomain`s;
   none is touched.
7. **`_forecast_request` / `_assemble` are module-level functions** called only from
   `OpenMeteoProvider.project` and their unit tests — a signature change is a same-stage
   mechanical update of those call sites.
8. **No re-export layer**: `manifold/__init__.py` is docstring-only; consumers import from
   `manifold.domain` directly. New types need no export wiring.

## Design decisions (align 2026-07-25 — restated only where they pin code)

Decisions of record live in the ticket; these are their implementation-binding forms.

1. **`SnappedAxis` is temporal-only and validates it.** Frozen dataclass
   `(name: AxisName, bounds: Interval[datetime])`; `__post_init__` raises `ValueError` unless
   both bounds are timezone-**aware** `datetime`s with `lower <= upper` (the "spatial sibling is
   a missing type" decision made real — a float-coordinate snapped axis is unrepresentable, and
   naive datetimes would poison aware comparisons downstream). `extent` returns `bounds`;
   `matches(declared)` returns `self.bounds.intersects(declared.extent)`. Not an
   `EnumerableAxis`; direct `Axis` subclass beside `ContinuousAxis`.
2. **`SelectableAxis = RegularAxis | VantageAxis | SnappedAxis`** (a `type` alias in
   `domain.py`). Plain `IntervalAxis` (exact-layer Z addressing) joins the union when alias
   desugaring gets its driver (roadmap Phase 4) — not now.
3. **`SelectionDomain`** is a frozen dataclass `(axes: Mapping[AxisName, SelectableAxis])`,
   direct `Domain` subclass (never `EnumerableDomain`), validated by the existing
   `_validate_four_axes`; `axis(name)` returns the member (structurally `Separable`);
   `matches(other)` composes per-axis over a `Separable` other exactly like
   `FootprintDomain.matches` (total: `False` for non-separable), `intersect` raises
   `NotImplementedError` like its peers. Nothing anywhere narrows `Selection.domain` to it.
4. **The v1 leaf serves exactly one `SelectionDomain` shape: T snapped, X/Y/Z enumerable.** Any
   snapped non-T axis, or a non-snapped T inside a `SelectionDomain`, is `CapabilityMismatch`
   (an unservable request shape — same category as the existing non-`Separable` guard; nothing
   authors those shapes in v1, and 003c authors only snapped-T). The isinstance-narrowing on the
   `SelectableAxis` union makes this guard statically exhaustive.
5. **Fetch bounds** (snapped branch of `_forecast_request`):
   `window = cadence.valid_time(clock.now())`, then
   `fetch_start = max(floor_to(bounds.lower, HOURLY_STEP), window.lower)` and
   `fetch_end = min(floor_to(bounds.upper, HOURLY_STEP), window.upper)` — flooring the upper
   bound *is* end-inclusivity ("last tick ≤ end"), flooring the lower bound *is* resolver-side
   cell containment. **Guard before any vendor call:** `fetch_end < fetch_start` →
   `CapabilityMismatch` (the raced-empty decision; admission answers the plain no-overlap case
   before the leaf is ever invoked).
6. **Answer realization** (snapped branch of `_assemble`): the answer's domain is a new
   `GridDomain` — X, Y, Z taken from the request's `SelectionDomain` (closed-projection
   semantics on the non-snapped axes: the vantage Z cell rides exactly as today), T taken from
   the native records' vendor-derived `RegularAxis`. The request object is never reused as the
   answer domain.
7. **Coherence validation** (snapped branch, all → `RuntimeFailure` naming the violation):
   every native record carries the *same* T axis (compare to the first); that axis's step is
   `HOURLY_STEP` (the leaf's own cadence claim); first tick ≥
   `floor_to(bounds.lower, HOURLY_STEP)`; last tick ≤ `bounds.upper`; every
   `ParameterData` length equals the T count. Regularity itself is fact 3's existing normalizer
   check. Shorter-than-requested vendor data that passes these checks is an **honest shorter
   answer** — no length-vs-request assertion exists on this branch.
8. **Provenance, parameters, Z-relabeling, and the enumerable branch are unchanged** — the
   `GridDomain` branch of `_assemble` keeps its strict `len(values) == len(sel.domain)`
   assertion verbatim (006's store refill depends on it).

## Code shapes

### `manifold/domain.py` (additive only)

```python
@dataclass(frozen=True)
class SnappedAxis(Axis):
    """Bounds-only request axis: the resolver's grid supplies anchor and step (ADR-0002)."""
    name: AxisName
    bounds: Interval[datetime]

    def __post_init__(self) -> None:
        # temporal-only member; aware-UTC convention (naive would poison comparisons)
        for edge in (self.bounds.lower, self.bounds.upper):
            if not isinstance(edge, datetime) or edge.tzinfo is None:
                raise ValueError(...)
        if self.bounds.upper < self.bounds.lower:
            raise ValueError(...)

    @property
    def extent(self) -> Interval: return self.bounds

    def matches(self, declared: Axis) -> bool:
        return self.bounds.intersects(declared.extent)   # type: ignore[arg-type]


type SelectableAxis = RegularAxis | VantageAxis | SnappedAxis


@dataclass(frozen=True)
class SelectionDomain(Domain):
    """Request-side representation: SelectableAxis per axis; structurally Separable,
    never enumerable, never nominally narrowed-to (Selection.domain stays Domain)."""
    axes: Mapping[AxisName, SelectableAxis]

    def __post_init__(self) -> None: _validate_four_axes(self.axes)
    def matches(self, other: Domain) -> bool: ...   # per-axis like FootprintDomain; total
    def intersect(self, other: Domain) -> Domain: raise NotImplementedError
    def axis(self, name: AxisName) -> SelectableAxis: return self.axes[name]
```

Placement: `SnappedAxis` after `ContinuousAxis`; `SelectionDomain` after `FootprintDomain`;
the alias between them. No other file in `manifold/` changes.

### `nodes/providers/open_meteo.py`

`_forecast_request(selection, taps, *, clock, cadence)` (two new keyword params; `project`
passes `self._clock` / `self._cadence`; direct-call tests updated same stage):

```python
domain = selection.domain
# existing Separable / float / X-Y reads unchanged
t_axis = domain.axis(AxisName.T)
if isinstance(domain, SelectionDomain):
    _require_snapped_t_only(domain)               # decision 4 → CapabilityMismatch
    assert isinstance(t_axis, SnappedAxis)
    window = cadence.valid_time(clock.now())
    fetch_start = max(floor_to(t_axis.bounds.lower, HOURLY_STEP), window.lower)
    fetch_end = min(floor_to(t_axis.bounds.upper, HOURLY_STEP), window.upper)
    if fetch_end < fetch_start:
        raise CapabilityMismatch("open-meteo window has rolled past the requested bounds")
else:
    fetch_start, fetch_end = t_extent.lower, t_extent.upper   # existing path, verbatim
# FetchRequest built from fetch_start/fetch_end exactly as today
```

`_assemble(records, selection)` dispatch replaces the current `GridDomain`-only guard:

```python
if isinstance(selection.domain, GridDomain):      # existing strict path, verbatim
    ...
elif isinstance(selection.domain, SelectionDomain):
    return _assemble_snapped(records, selection)  # decisions 6-7
else:
    raise CapabilityMismatch(...)                 # today's message, category unchanged
```

`_assemble_snapped`: validate coherence (decision 7), build
`GridDomain({X: sel.X, Y: sel.Y, Z: sel.Z, T: records_t_axis})`, fill `ranges` /
`parameters` / provenance exactly as the enumerable path does (same missing-parameter and
no-records `RuntimeFailure`s), return a `CoverageRecord` on the realized domain.

### `tests/deterministic/fakes.py`

One new helper, mirroring `point_timeline_domain`:
`snapped_point_domain(*, lon=1.0, lat=2.0, start, end) -> SelectionDomain` (X/Y count-1
`RegularAxis`, Z `VantageAxis(Interval(0.0, 10.0))`, T `SnappedAxis`).

## Flows

**Snapped request (engine-level, v1 wiring):** test/embedder builds
`Selection(SelectionDomain(..., T=SnappedAxis(bounds)), params)` → `Gateway.resolve` →
`Arbiter.project`: per-parameter `serves` → `FootprintDomain.matches` → per-axis gate (T
intersects the live `RollingAxis` window; X/Y containment; Z vantage as today) → single winner →
pass-through `Reservoir` → leaf: fetch `bounds ∩ window` (floored) → normalizer (existing
semantic + regularity validation) → `_assemble_snapped` coherence → `CoverageRecord` on
{request X/Y/Z, vendor T}. Shorter vendor data → shorter honest answer.

**Enumerable request:** every path byte-identical to today (edge included).

**Failure surface (complete):** no producer intersects → `CapabilityMismatch` at the Arbiter
(today's message); raced-empty at fetch → `CapabilityMismatch` (leaf, pre-fetch); malformed
snapped shape (snapped non-T / non-snapped T in a `SelectionDomain`) → `CapabilityMismatch`
(leaf guard); vendor garbage — gapped/non-hourly times, out-of-bounds ticks, record T
disagreement, length mismatch — → `RuntimeFailure`. `BadRequest` is unreachable (no edge
change). No new error categories, no logging changes ([#14](../concerns.md#14-resolution-trace-and-observability) unowned here).

## Implementation stages

Each stage ends with `uv run ruff check . && uv run ruff format --check . && uv run pyright &&
uv run pytest` green.

1. **`SnappedAxis`** — RED (`tests/deterministic/manifold/test_domain.py`): aware-datetime and
   ordering validation (`ValueError` on naive, float, or reversed bounds; equal bounds legal —
   the "current conditions" instant); `extent == bounds`; `matches` is intersection (overlap
   admits, disjoint rejects, boundary-touch admits, containment *not* required) against
   `ContinuousAxis` and `RollingAxis` declared extents (`fakes.STOPPED`). GREEN: the class.
2. **`SelectionDomain` + admission pinning** — RED: four-axes validation; `axis()`;
   `matches` totality (non-separable → `False`); then the composition tests expected to pass
   with *no code beyond stage 1–2 types* — `FootprintDomain.matches(selection_domain)` admits
   an overlapping snapped T and rejects no-overlap, X/Y containment still gates, and
   `Arbiter.project` with a `FakeProvider` (`fakes.footprint_capability`) admits a snapped
   Selection / raises `CapabilityMismatch` on no overlap. These pins *are* the
   non-duplication proof: if any needs engine code, the shape is wrong. GREEN: the class +
   `snapped_point_domain` fake.
3. **Leaf fetch bounds** — RED (`tests/deterministic/nodes/providers/test_open_meteo.py`,
   mocked transport, `StoppedClock`): bounds inside the window → `start_hour`/`end_hour` are
   the floored bounds; bounds straddling both edges → clamped to the window; mid-hour bounds →
   lower *and* upper floored (end-inclusivity); `bounds.upper` before the window → 
   `CapabilityMismatch` with **no vendor call**; snapped X (hand-built malformed
   `SelectionDomain`) → `CapabilityMismatch`, no vendor call. GREEN: the
   `_forecast_request` branch, signature change, `project` call site, direct-call test updates.
4. **Snapped assembly + coherence** — RED: canned response matching the fetch window → Coverage
   whose domain is {request X/Y/Z, vendor-derived T} and whose payload values pass through;
   canned response *shorter* than requested bounds → honest shorter Coverage, no failure;
   response ticks before `floor(bounds.lower)` or after `bounds.upper` → `RuntimeFailure`;
   non-hourly times → `RuntimeFailure` (normalizer pin, kept); all existing enumerable-path
   tests untouched and green. GREEN: `_assemble` dispatch + `_assemble_snapped`.
5. **Engine e2e + docs + status** — RED (`tests/deterministic/test_e2e_forecast.py`): a woven
   server profile resolved through `Gateway.resolve` with a snapped Selection over the canned
   transport (bypassing the MCP edge, which stays enumerable) → full payload assertions; plus
   one live-suite run `uv run pytest tests/parity` **unchanged** (m4 acceptance: parity is
   untouched). GREEN — docs at landing:
   [ADR-0004](../adr/0004-producer-resolution-and-capability.md) admission language becomes
   mode-dependent (containment for enumerable, intersection for snapped);
   [#13](../concerns.md#13-candidate-admission-containment-vs-intersection) records the scoped
   v1 position; ADR-0002 gains the `SelectionDomain` / `SelectableAxis` representation bullet
   (answers realized from requests); [delivery status](../tickets/README.md) m4 row → Done and
   execution-order note; ticket + this RFC → `done/`.

## Compatibility and rollout

- **Zero caller-visible change**: the MCP schema, semantics, and payloads are untouched; no
  config or env change; no migration. The mode becomes reachable only to embedders/tests until
  003c rewires the edge.
- The deterministic suite must stay green after every stage; the enumerable request path is
  never edited, only branched around.

## Scope limits and follow-ups

- **003c** consumes the mode (edge parsing, reach-filled default `end`, narration) — its ticket;
  the live snapped end-to-end run is 003c's landing probe.
- **006** inserts the store-side half (`quantize` consuming snapped Selections); the
  [#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) carve and
  [#23](../concerns.md#23-spatial-vs-temporal-regularaxis-types) split stay untriggered here —
  #23's embedding-vocabulary constraint (split invisible to request authors) is recorded at
  #23/#39.
- **Snapped X/Y** = mint the spatial sibling type + edge wiring (Grid-realization driver);
  **open-ended bounds** (`upper = None`) deferred to
  [#30](../concerns.md#30-response-membership-under-runtime-degraded-fallback)'s
  diverging-reach trigger; **plain `IntervalAxis` in `SelectableAxis`** waits for alias
  desugaring (Phase 4).
- **Mixed-reach multi-winner snapped windows** (two winners resolving different T extents →
  the Arbiter's domain-equality check fails loudly): the recorded #30 revisit, triggered by the
  second provider with diverging reach — deliberately not handled here.
- `resample`'s non-enumerable guard message (it says "continuous") is slightly narrow for a
  snapped Selection; unreachable in v1 wiring, left for 006's read-back work.
