# RFC 0015 · 2026-08-08 · Per-parameter materialized capability — implementation plan

Implementation plan for [per-parameter materialized
capability](../../tickets/done/01-0113-per-parameter-materialized-capability.md). Settles the two questions
the ticket delegates here: the form's **name** and its **shape**.

**Scope in one line:** `FootprintCapability` becomes **`GranularCapability`** — one class, no type
parameter — whose name and docstring are true of both its uses, so the carrier and the timeline store
advertise through it instead of waiting for a form to be minted.

**The cell was never missing a class.** It was missing a *sanctioned* one. Today's class is named for
a Provider declaration and its docstring closes the door on the other use outright:

```python
"""General leaf (a `Provider`'s declaration): per-parameter covered `Domain` footprint.
   … only the materialized `EnumerableCapability` narrows its reach to an `EnumerableDomain`."""
```

A carrier or a Store reading that concludes, correctly, that this form is not for it — which is why
[RFC 0012 d.3](./0012-20260808-multidomain-carrier-timeline.md) and
[RFC 0013 d.6](../0013-20260808-timeline-store.md) each deferred the form's name and shape rather than
just constructing one. Making the class honest *is* the deliverable.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| The capability family | [ADR-0007](../../adr/0007-capability-carries-its-domain.md) | `FootprintCapability` renamed `GranularCapability`; field `footprints` → `reaches`; docstring covers both uses. The family table gains the materialized per-parameter row. No new type, no type parameter. |
| "materialized ⇒ enumerable reach" | ADR-0007 | **Explicitly scoped to the co-domained `EnumerableCapability`**, where it is stated in the type. It is not claimed of the per-parameter form (decision 2). |
| Materialized-**provider** discriminator | [ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md), [#37](../../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization) | **Untouched** — stays `isinstance(provider.capability, EnumerableCapability)` ([composition.py:50](../../../src/meteoscape/nodes/composition.py)). |
| *Footprint* (the term) | [glossary](../../glossary.md) | **Untouched** — still "one producer's declared span … before composition". The class stops being named after one of its two uses; the concept does not move. `_declare_footprints` / `_footprints` in `timeline.py` keep their names. |
| `UnionCapability`, `DerivedCapability`, `EnumerableCapability` | ADR-0007 | **Untouched.** `UnionCapability` in particular does not merge into this form (decision 4). |
| Composition-failure attribution | [#46](../../concerns.md#46-composition-failure-attribution-is-paid-inside-geometry) | **Untouched** — deferred; this RFC neither depends on nor disturbs it. |

## Facts that shape the implementation (verified 2026-08-08)

1. **No caller consumes a narrowed reach.** Every `.reach()` site takes the result as `Domain`:
   `_t_extent(capability.reach(p))` at [mcp_app.py:159, 219](../../../src/meteoscape/api/mcp_app.py),
   the dominance fold at [arbiter.py:241](../../../src/meteoscape/nodes/arbiter.py), the contained-in-all
   fold at [capability.py:188](../../../src/meteoscape/manifold/capability.py). `EnumerableCapability`'s
   *existing* covariant narrowing likewise has no consumer — it is pinned solely by its own
   `assert_type` test ([test_capability.py:148](../../../tests/deterministic/manifold/test_capability.py)).
2. **Neither future consumer reads a narrow reach back, either.** The carrier holds its capability as
   the protocol (`_capability: Capability`, [RFC 0012 d.3](./0012-20260808-multidomain-carrier-timeline.md));
   the `Reservoir` reads the store's `report`, not its capability's reach
   ([RFC 0013 d.5–d.6](../0013-20260808-timeline-store.md)).
3. **Enumerability is already guaranteed upstream of both.** The carrier's entries come from
   `record.domain` — enumerable by the `Coverage` invariant ([core.py:82](../../../src/meteoscape/manifold/core.py))
   — and the store's from its `GridDomain` units. A type parameter would restate a guarantee the
   construction sites already hold, for no reader.
4. **Runtime generic erasure.** `isinstance(x, GranularCapability)` cannot distinguish
   parameterizations, so ADR-0006's materialized-provider discriminator could not rest on a generic
   form even if one existed — which is precisely the justification ADR-0007 offers for
   `EnumerableCapability`'s narrowing. The justification does not transfer.
5. **Pyright infers PEP 695 class type parameters as invariant here** (probed against `pyright`
   1.1.410): `class GranularCapability[DomainT: Domain = Domain]` makes
   `GranularCapability[FootprintDomain]` fail a bare `GranularCapability` annotation, breaking
   [timeline.py:110](../../../src/meteoscape/nodes/providers/timeline.py) and every test helper's return
   type. Recovering it needs the legacy `TypeVar(..., covariant=True, default=Domain)` spelling plus a
   comment forbidding future modernization. Recorded as **evidence against** the generic, not as an
   instruction (decision 2).

## Design decisions

1. **The name is `GranularCapability`; the field is `reaches`.**

   The family sorts on *one reach for all parameters* vs *per parameter*, and *own geometry* vs
   *delegated to members*. This form is per-parameter-and-own-geometry, and it serves two uses: a
   Provider's **declared** footprints and a carrier's or Store's **held** records. `Footprint` names
   only the first — the glossary defines it as a producer's own span *before composition* — so a name
   drawn from it is false for half the form's uses, which is exactly the confusion that made two RFCs
   defer.

   `Granular` is not a coinage: [ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md)
   already uses it for this contrast ("unit-granular, never co-domained"), applied to Store units
   rather than capability reaches. Reusing it reduces vocabulary rather than adding to it. The
   docstring must state the one place the usages differ, or a reader arriving from ADR-0006 will
   over-read it: **a Store unit is granular in parameter *and* cells; this form is granular in
   parameter only.**

   The field becomes `reaches` — ADR-0007's own word for what a capability publishes per parameter,
   and the only word true of both uses. `_declare_footprints` and `_footprints` in `timeline.py` keep
   their names: a provider really does declare footprints, and ADR-0007 already says a leaf's
   footprint *is* its reach, so `GranularCapability(reaches=self._footprints)` states that identity
   rather than blurring it.

2. **No type parameter. `reach` returns `Domain`, for every use of the form.**

   The generic was the working direction at ticket time; the evidence rejects it. Nothing consumes a
   narrowed reach today (fact 1), neither queued consumer will (fact 2), and enumerability is already
   guaranteed where the values are built (fact 3). What the parameter would buy is a *statement* —
   "materialized ⇒ enumerable reach" — whose stated purpose in ADR-0007 is to give the
   materialized-provider discriminator something to rest on, which erasure forbids for a generic
   (fact 4). It would buy a true sentence and no caller anything.

   It is not free, either. Written the modern way it silently infers invariant and breaks existing
   annotations; recovering covariance means a legacy `TypeVar` spelling carrying a comment telling
   future readers not to tidy it (fact 5). **A workaround needed to satisfy a requirement with no
   consumer is evidence against the requirement, not a design.**

   So the class is today's class, renamed, with an honest docstring:

   ```python
   @dataclass(frozen=True)
   class GranularCapability:
       """Per-parameter own-geometry leaf: one `Domain` per parameter, published as its reach.

       Two uses, one form: a `Provider`'s declared footprints, and a materialized per-parameter
       holder — a multi-domain carrier or a retentive `Store` — whose reaches happen to be
       enumerable. The form does not distinguish them: `reach` publishes a general `Domain` either
       way, and no caller consumes a narrower type (ADR-0007). "Materialized ⇒ enumerable reach" is
       claimed only of the co-domained `EnumerableCapability`, whose single `domain` field carries
       the grid `Coverage` is co-domained on.

       Granular **in parameter only**: each parameter carries its own `Domain`, whatever cells that
       Domain covers. ADR-0006's unit granularity is finer (parameter *and* cells) — the shared word
       names the same co-domained-vs-per-parameter axis, not the same partition.
       """

       reaches: Mapping[ParameterId, tuple[ParameterDef, Domain]]
   ```

   Bodies are unchanged from today's `FootprintCapability` — `parameters`, `serves`, `reach` — only
   the field name moves.

3. **ADR-0007's claim is scoped, not widened.** The distinction is easy to invert by accident, so the
   edit is given verbatim rather than as intent. In the "Two contract details ride on the table"
   paragraph, **replace**:

   > And **`EnumerableCapability.reach` narrows covariantly to `EnumerableDomain`** — the materialized
   > form's reach *is* its grid, so "materialized ⇒ enumerable reach" is stated in the type, where the
   > materialized-provider discriminator ([ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md))
   > can rest on it.

   **with**:

   > And **`EnumerableCapability.reach` narrows covariantly to `EnumerableDomain`** — the co-domained
   > form's reach *is* its grid, so "materialized ⇒ enumerable reach" is stated in the type **for that
   > form**. It is deliberately *not* claimed of the per-parameter `GranularCapability`: its
   > materialized use (a multi-domain carrier, a retentive `Store`) publishes enumerable domains as a
   > fact of construction, and no caller reads a reach back at the narrower type. The
   > materialized-**provider** discriminator
   > ([ADR-0006](../../adr/0006-materialization-granularity-and-store-shape.md)) rests on the *class*
   > `EnumerableCapability`, never on a reach type — a parameterized form could not carry it at all,
   > since parameterization is erased at runtime.

   Two ways to get this wrong, both worse than leaving it alone: **widening** the claim to both forms
   (the opposite of this decision), or **dropping** the discriminator clause, which belongs to
   [#37](../../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization) and is not
   this ticket's to touch. Note the replacement says `capability.domain`'s job, not `reach`'s — what
   `Coverage` actually consumes is the class narrowing and the `domain` field
   ([core.py:83](../../../src/meteoscape/manifold/core.py): `Countable.domain` is "derived from
   `capability.domain`"), not a narrowed `reach` return.

   The family table becomes:

   | Form | Whose | `reach(parameter)` |
   |---|---|---|
   | `GranularCapability` | a Provider leaf, a multi-domain carrier, or a retentive `Store` | that parameter's own `Domain` — declared footprint or held record |
   | `EnumerableCapability` | a materialized Coverage | its grid (narrowed to `EnumerableDomain` in the type) |
   | `UnionCapability` | an Arbiter | the dominating producer's domain |
   | `DerivedCapability` | a Calculator | the domain contained in all inputs' |

   One row now covers both uses, which is the point: the cell is filled by a form that admits it, not
   by a fifth entry.

4. **`UnionCapability` does not merge into this form, and the RFC says why.** Structurally it looks
   close — per-parameter reaches, one entry each. It differs in `serves`, which delegates
   (`any(m.serves(…))`) rather than reading its own composed reach. That delegation is what keeps a
   member free to tighten below its declared geometry (resampler-reachability, probed availability);
   ADR-0007 lists deriving `serves` from `reach` as a **rejected alternative** for exactly that reason.
   The two are geometrically equivalent only while `serves` is pure geometry everywhere, which is an
   accident of v1, not a property. The de-keying of `UnionCapability.members` — a separate finding, its
   keys being unread — belongs to [#46](../../concerns.md#46-composition-failure-attribution-is-paid-inside-geometry)
   and is not touched here.

## Stages (each green)

Stages are landing milestones, not single red→green cycles: within each, work proceeds one observable
behavior → minimal implementation at a time per `/tdd`. This slice adds no behavior, so neither stage
has a red phase — the suite is green throughout, which is the point of a rename.

1. **Rename** — two renames with *different* reach. Do them in one pass; the suite is green before and
   after, since nothing behavioral moves.

   **The class**, `FootprintCapability` → `GranularCapability`: the declaration in
   `manifold/capability.py`; `nodes/providers/timeline.py` at
   [:24](../../../src/meteoscape/nodes/providers/timeline.py) (import),
   [:92](../../../src/meteoscape/nodes/providers/timeline.py) (construction) and
   [:110](../../../src/meteoscape/nodes/providers/timeline.py) (the property's return annotation); the
   `nodes/providers/base.py` [:6](../../../src/meteoscape/nodes/providers/base.py) docstring; and five
   test modules — `fakes.py`, `manifold/test_capability.py`, `nodes/test_arbiter.py`,
   `nodes/test_calculator.py`, `nodes/test_composition.py`.

   **The field**, `footprints` → `reaches`, in exactly three kinds of place and nowhere else: the
   dataclass field declaration ([capability.py:65](../../../src/meteoscape/manifold/capability.py)); its
   three `self.footprints` reads inside the class
   ([capability.py:69, 72, 77](../../../src/meteoscape/manifold/capability.py)); and the
   `footprints=` keyword at every construction site. Plus **one attribute read outside the class, in a
   module that names neither the class nor the keyword** and is therefore invisible to a class-name
   search: `provider.capability.footprints` and `capability.footprints.items()` at
   [test_open_meteo.py:455, 474](../../../tests/deterministic/nodes/providers/test_open_meteo.py).

   **Identifiers named `footprints` that must NOT change** — they are locals, parameters, and a helper,
   not the field. A blind search-and-replace corrupts every one:

   | Site | What it is |
   |---|---|
   | [timeline.py:306, 323](../../../src/meteoscape/nodes/providers/timeline.py) | `_declare_footprints` and its local `footprints` dict |
   | [timeline.py:83, 92](../../../src/meteoscape/nodes/providers/timeline.py) | `self._footprints` |
   | [test_arbiter.py:514](../../../tests/deterministic/nodes/test_arbiter.py) | the `footprints` **parameter** of `_multi_producer` |
   | [test_open_meteo.py:455](../../../tests/deterministic/nodes/providers/test_open_meteo.py) | the local binding (rename the attribute read, keep the local's name) |

   These stay because a provider really does declare footprints — ADR-0007 says a leaf's footprint *is*
   its reach, so `GranularCapability(reaches=self._footprints)` states that identity rather than
   blurring it (decision 1).
2. **The docstring and the docs.** The class docstring of decision 2 is the actual deliverable — the
   form declaring itself open to both uses. Then, and **these are not all the same edit**:

   | Site | Edit |
   |---|---|
   | [ADR-0007](../../adr/0007-capability-carries-its-domain.md), contract-details paragraph | The verbatim replacement of decision 3 |
   | ADR-0007, family table | The four rows of decision 3 |
   | [ADR-0002:64, 97](../../adr/0002-data-model.md) | Class-diagram node name and relation — **name only** |
   | [ADR-0002:65](../../adr/0002-data-model.md) | The field **inside** the node: `Map~ParameterId, (ParameterDef, Domain)~ footprints` → `reaches` |
   | [ADR-0004:255](../../adr/0004-producer-resolution-and-capability.md) | **Name only** — "whose `FootprintCapability` advertises the network's aggregate hull" |
   | [ADR-0004:55](../../adr/0004-producer-resolution-and-capability.md) | **Not a name swap.** It reads "a general leaf (**a `Provider`'s declaration**)" — the exact framing this ticket exists to retire. Reword to name both uses, as the class docstring does |
   | [RFC 0012 d.3](./0012-20260808-multidomain-carrier-timeline.md) | Replace "the per-parameter materialized form landed by … which owns its name and shape" with the landed name |
   | [RFC 0013 d.6](../0013-20260808-timeline-store.md) | Same: its capability paragraph names `GranularCapability` outright |
   | [glossary](../../glossary.md), *Footprint* | Re-read, **left as written** (decision 1) |

   The last two RFC edits are what make the ticket's "neither consuming slice has grounds to defer
   again" criterion checkable rather than a judgment call: those two deferral sentences *are* the
   deferral, and rewriting them is the evidence. Both RFCs are active plans for unstarted tickets, not
   historical records. Historical records — [`tickets/done`](../../tickets/done) and [`rfc/done`](.)
   — are left as written per the [documentation map](../../README.md).

   ADR-0004:55 is the one edit that can pass review while failing the ticket: swap only the name and the
   ADR still asserts the form is a Provider declaration, which is the falsehood the rename exists to
   remove.

## Out of scope / follow-ups

- **The carrier and store constructing the form** — theirs, at
  [0115.0020](../../tickets/done/01-0115.0020-multidomain-carrier-timeline.md) and
  [0115.0030](../../tickets/01-0115.0030-timeline-store.md). This slice lands the form unwired to them.
- **A type-level enumerable narrowing on this form** — rejected here for want of a consumer
  (decision 2). **Trigger to revisit:** the first caller that reads
  `carrier_or_store.capability.reach(p)` and needs the result *typed* enumerable rather than merely
  being enumerable. Then the covariance evidence in fact 5 is the starting point, not a rediscovery.
- **Geometry's identity and operator prose**, the duplicated separability guard, and
  `UnionCapability`'s unread keys → [#46](../../concerns.md#46-composition-failure-attribution-is-paid-inside-geometry).
- **Whether `EnumerableCapability` remains the right materialized-provider discriminator** →
  [#37](../../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
- **Collapsing `EnumerableCapability` into `GranularCapability`** by giving it a co-domained
  constructor — not proposed. It is co-domained *by construction* (one `domain` field, not a map), and
  that is what `Coverage.capability` narrows to and `Countable.domain` derives from
  ([core.py:82–90](../../../src/meteoscape/manifold/core.py)); flattening it would put a
  same-domain-for-every-parameter invariant into a map that cannot state it.
