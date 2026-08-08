# RFC 0011 · 2026-08-08 · `ANY` as the boundless snapped member — implementation plan

Implementation plan for [`ANY` as the boundless snapped member](../tickets/done/01-0115.0010-any-boundless-member.md)
(slice 1 of the [retentive store](../tickets/01-0115-retentive-store-freshness.md), whose align
record carries the *why*). This plan is the single way to build it.

**Scope in one line:** `SnappedAxis` becomes a standalone axis with optional bounds (`None` = `ANY`),
`ground` gains the take-the-axis-whole arm, and `RegularAxis.clip` gains the boundary tolerance under
one index-space policy. `manifold/domain.py` only; no live caller changes behavior.

## Boundaries involved

| Boundary | Owner | What this does to it |
|---|---|---|
| `SnappedAxis` (`manifold/domain.py`) | [ADR-0002](../adr/0002-data-model.md) | Stops subclassing `ContinuousAxis`; stands alone on `Axis` with `interval: Interval[datetime] \| None`. `SelectableAxis` union unchanged. |
| `ground` | ADR-0002 / [ADR-0001](../adr/0001-manifold-algebra-and-composition.md) | Third per-axis arm: boundless member → answering axis whole. Pinned/bounded arms byte-identical. |
| `RegularAxis.clip` | ADR-0002 | Gains `LATTICE_TOLERANCE` in its floor/ceil, still one branch-free expression. |
| `LATTICE_TOLERANCE` / `sub_lattice_offset` | ADR-0002, [#22](../concerns.md#22-lattice-helpers-vs-domain--sampling-module-split) | The constant is redefined **index-space (dimensionless)**; `sub_lattice_offset`'s float arm converts to the same form. One policy, one constant. |
| `agreed_geometry`, all nodes, edges | — | **Untouched** — the open-axis licence arrives with the carrier ([RFC 0012](./0012-20260808-multidomain-carrier-timeline.md)), which owns both call sites. |

## Facts that shape the implementation (verified 2026-08-08)

1. `SnappedAxis` appears in exactly two modules: `domain.py` (definition, `ground`, `SelectableAxis`)
   and `mcp_app.py:169` (the edge's bounded author). No other construction or `isinstance` site.
2. `Axis.matches` defaults to containment via `self.extent`; `SnappedAxis` overrides to
   intersection (`domain.py:292`). `contains_extents` / `split_extents` read `extent` on **declared**
   domains only — no live caller reads a request member's extent.
3. The class comment at `domain.py:254` ("base of the request `SnappedAxis`") and ADR-0002's
   equivalent sentence describe the subclassing this RFC removes — both swept at stage 1.
4. `RegularAxis.clip` applies no tolerance today (`floor`/`ceil` raw); only T is snapped live and
   `timedelta` division is exact, so current behavior is preserved by any epsilon ≪ 1 tick.
5. `sub_lattice_offset`'s float arm checks `abs(inner.anchor − aligned) > LATTICE_TOLERANCE` with
   the constant in **absolute degrees** (`1e-9`); steps in this codebase are ≥ 0.05°, so the
   index-space equivalent (`1e-9` dimensionless → ≥ `5e-11` degrees) is tighter yet still ~4 orders
   above float noise — no fixture can flip.

## Design decisions

1. **Standalone class, not a widened subclass field.** Redeclaring `ContinuousAxis.interval` as
   `Interval[datetime] | None` in a subclass breaks the parent's contract (`extent` promises an
   `Interval`); pyright would be right to complain. So:

   ```python
   @dataclass(frozen=True)
   class SnappedAxis(Axis):
       """Bounds-only request axis; without bounds (the default) it is the boundless form (`ANY`) —
       the axis is left entirely to the producer. The resolver's grid supplies anchor and step
       (ADR-0002)."""
       interval: Interval[datetime] | None = None

       @property
       def extent(self) -> Interval:
           if self.interval is None:
               raise ValueError(f"open {self.name.value} member has no extent")
           return self.interval

       def matches(self, declared: Axis) -> bool:
           return self.interval is None or self.interval.intersects(declared.extent)

       def clip(self, bounds: Interval) -> Axis | None:
           # A snapped axis is the bounds another axis is clipped to; it is never asked for a
           # part of itself. Kept total for the Axis contract:
           if self.interval is None:
               return self
           overlap = self.interval.intersection(bounds)
           return None if overlap is None else SnappedAxis(self.name, overlap)
   ```

   The `__post_init__` tz/ordering checks run only when `interval is not None`. A *bounded* spatial
   member stays a type error exactly as today (`Interval[datetime]`).
2. **`ground`'s third arm precedes the bounded arm** and reuses the existing separability guard:

   ```python
   member = request.axes[name]
   if not isinstance(member, SnappedAxis):
       axes[name] = member                     # pinned — identity (unchanged)
       continue
   if answering is None:
       raise ValueError(f"a snapped {name.value} grounds only against separable geometry")
   if member.interval is None:                 # ANY — take the answering axis whole
       whole = answering.axis(name)
       if not isinstance(whole, EnumerableAxis):
           raise ValueError(f"an open {name.value} needs cells; the answering axis is a span")
       axes[name] = whole
       continue
   part = answering.axis(name).clip(member.interval)   # bounded — unchanged
   ...
   ```

   Cells are still `ground`'s requirement, not `clip`'s (ADR-0002); an open member against a
   declared span declines with the same vocabulary as the bounded arm.
3. **One tolerance policy, stated in index space.** `LATTICE_TOLERANCE` is redefined as a
   dimensionless index-space epsilon (`1e-9`, "fraction of one step"); both consumers use it:

   ```python
   # RegularAxis.clip — the epsilon rides the already-dimensionless quotient:
   low = (bounds.lower - self.anchor) / self.step
   first = max(0, floor(low + LATTICE_TOLERANCE) if self.cellular else ceil(low - LATTICE_TOLERANCE))
   last = min(self.count - 1, floor((bounds.upper - self.anchor) / self.step + LATTICE_TOLERANCE))

   # sub_lattice_offset float arm — same constant, same space:
   quotient = delta / step
   offset = round(quotient)
   if offset < 0 or abs(quotient - offset) > LATTICE_TOLERANCE:
       return None
   ```

   `clip` stays one expression with no `isinstance`: the quotient is a plain float for both
   coordinate kinds, so the epsilon applies to T too (≤ 3.6 µs on an hourly lattice — inert). The
   guard test asserts `domain.py` defines exactly one tolerance constant and both sites reference
   it (a second diverging constant fails the guard).

## Stages (each green)

Stages are landing milestones, not single red→green cycles: within each, work proceeds one
observable behavior → minimal implementation at a time per `/tdd`; the single-constant guard is
to-tickets' machine-enforced-constraint form, not a behavior test.

1. **Member** — red: construction (boundless on any axis; bounded spatial rejected), `matches`
   (open admits everything), `extent` (open raises, message names the member). Green: the
   standalone class; sweep the two "base of `SnappedAxis`" comments (`domain.py:254`, ADR-0002).
2. **Ground** — red: open member → answering axis whole (T and Z cases); open member against a
   declared span declines; existing pinned/bounded tests untouched and green throughout.
3. **Tolerance** — red: boundary-point test (a bound float-noise below a cell edge lands in the
   containing cell; the same input floored one cell early before), T-resolution regression pins,
   and the single-constant guard. Green: the index-space rewrite of `clip` + `sub_lattice_offset`.

## Out of scope / follow-ups

- The group-returning fold, the carrier, and every node/edge touch → [RFC 0012](./0012-20260808-multidomain-carrier-timeline.md).
- `quantize` (the first in-tree author of a boundless member) → RFC 0013.
- One-sided bounds stay unrepresentable; their author is 011/004 (parent ticket, *Request
  vocabulary*).
