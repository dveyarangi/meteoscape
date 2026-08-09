# Per-parameter materialized capability

- **Status:** Done
- **Type:** AFK
- **RFC:** [0015](../../rfc/done/0015-20260808-per-parameter-materialized-capability.md) — settles the
  form's name (`GranularCapability`) and its shape (one class, no type parameter — the enumerable
  narrowing is rejected for want of a consumer)
- **Outcome:** The capability family gains its missing cell — a named form for a **materialized
  per-parameter** holder — so the multi-domain carrier and the timeline store advertise the geometry
  they hold through one form instead of each inventing its own, and ADR-0007's family table and its
  "materialized ⇒ enumerable reach" claim are true as stated.

## What to build

Conversation-born maintenance (2026-08-08 capability-hierarchy review); this ticket carries its own
context.

The capability family sorts on two axes — *one reach for all parameters* vs *per parameter*, and
*admission from own geometry* vs *delegated to members*. One cell is empty:

| | general `Domain` | materialized (enumerable) |
|---|---|---|
| one shared reach | — | `EnumerableCapability` |
| per parameter | `FootprintCapability` | **missing** |

`EnumerableCapability` is co-domained, so it cannot hold parameters on differing native domains.
`FootprintCapability`'s reach widens to `Domain`, and no call site consumes a narrowing today.

Two queued slices need that empty cell filled, and both currently defer its name and shape here. The
multi-domain carrier ([0115.0020](./01-0115.0020-multidomain-carrier-timeline.md)) publishes one entry
per parameter drawn from its records' native domains ([RFC 0012
d.3](../../rfc/done/0012-20260808-multidomain-carrier-timeline.md)); the retentive timeline store
([0115.0030](../01-0115.0030-timeline-store.md)) assembles the same shape from its qualifying units'
domains ([RFC 0013 d.6](../../rfc/done/0013-20260808-timeline-store.md)). Both publish exactly
`parameter → (ParameterDef, EnumerableDomain)`.

Land that form. The **name** is not cosmetic: the glossary's *Footprint* is "one producer's
**declared** span … before composition", which is not what a carrier or a store publishes, so a form
covering both uses cannot keep a name drawn from one of them. The field name moves with it. The
**shape** was the RFC's call, and
[RFC 0015](../../rfc/done/0015-20260808-per-parameter-materialized-capability.md) settled it as *one
class, no type parameter*: the enumerable narrowing the ticket originally reached for has no consumer,
present or queued, and the justification ADR-0007 gives for the co-domained form's narrowing does not
transfer (runtime erasure). The cell was never missing a class — it was missing a class whose name and
docstring admitted the second use.

What does **not** move: `UnionCapability` stays a distinct form. ADR-0007 keeps `serves` delegated to
members rather than derived from composed `reach`, which is what leaves the resampler-reachability and
probed-availability seams open; a composite admitting from its own reach would bypass a member that
tightens below its declared geometry.

The rest of the 2026-08-08 review — geometry carrying producer identity and operator prose, the
duplicated separability guard, `UnionCapability`'s unread keys — is deferred at
[#46](../../concerns.md#46-composition-failure-attribution-is-paid-inside-geometry) until a
configuration can actually fail composition. Nothing in this ticket depends on it.

## Acceptance criteria

- [x] Behavior unchanged: the full suite is green through the reshape, and no existing call site's
      admission or reach answers differ.
- [x] A materialized per-parameter holder has one named capability form to advertise through, and the
      carrier and timeline-store slices can consume it without redeciding its name or its shape.
- [x] The form declares itself open to both uses: its name and docstring are true of a Provider's
      declared footprints **and** of a carrier's or Store's held records. The evidence is that the two
      consuming plans stop deferring — the carrier's and timeline store's RFCs name the form outright
      instead of pointing at one to be minted.
- [x] ADR-0007's family table names the form for both uses, and its "materialized ⇒ enumerable reach"
      claim is true as stated — scoped to the form that states it in the type and has a consumer for
      it.
- [x] Every maintained document naming the form uses its landed name; historical records
      (`done/` tickets and [resolved RFCs](../../rfc/done)) are left as written.

## Blocked by

None — could start immediately.

## Parent scope addressed

No parent — conversation-born maintenance, delivering no product capability. It unblocked the
[multi-domain carrier](./01-0115.0020-multidomain-carrier-timeline.md) and the
[retentive timeline store](../01-0115.0030-timeline-store.md), which advertise through the form it
landed.
