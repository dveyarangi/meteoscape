"""`Store` substrate and its construction face.

Home of the `Writable` facet (beside its sole realization — ADR-0001), the `Store` contract, and
the in-memory substrate. A store's whole public face is the Manifold contract + `Writable` +
`quantize`; its `project` is the holdings query — clockless and freshness-blind, so an archive
substrate serves deliberately stale history through the same face. The Weaver allocates every store
via an injected `StoreFactory` — it owns *where* stores exist; the factory owns *what* a store is.
See architecture.md ("Store") and ADR-0005/0006.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import timedelta
from math import floor
from typing import Protocol, runtime_checkable

from ..clock import Clock
from ..config import StoreSpec
from ..errors import CompositionError
from ..manifold.capability import Capability, EnumerableCapability, GranularCapability
from ..manifold.core import Manifold, Selection
from ..manifold.coverage import CoverageRecord, CoverageSet
from ..manifold.data import ParameterData
from ..manifold.domain import (
    AXIS_ORDER,
    AxisName,
    Domain,
    EnumerableAxis,
    GridDomain,
    Interval,
    RegularAxis,
    SelectableAxis,
    SelectionDomain,
    SnappedAxis,
    VantageAxis,
    as_separable,
    sub_lattice_offset,
)
from ..manifold.provenance import Provenance, Uniform
from ..parameters import ParameterDef, ParameterId


@runtime_checkable
class Writable(Protocol):
    """Facet: the materialization boundary - consume a natural answer and hold it in whole Holdings.

    Lives here rather than in the read-only algebra (`manifold/core.py`) because the `Store` is its
    sole realization and the store's face is where ADR-0006 names it. The signature takes the
    answer's natural grouped shape; the caller normalizes a single record with `CoverageSet.of`, so
    an implementation never branches on answer shape.
    """

    async def assimilate(self, answer: CoverageSet) -> None: ...


@runtime_checkable
class Store(Manifold, Writable, Protocol):
    """The substrate a `Reservoir` owns: a Writable Manifold leaf.

    Holds sampled Coverages in whole assimilable Holdings (a Holding is replaced atomically, so it carries
    one origin); the only `assimilate` target. Its `capability` *narrates* holdings — plural cells
    per parameter truncate to one reach
    ([#47](../../../docs/concerns.md#47-a-stores-capability-narrates-plural-holdings-truncate-to-one-reach));
    the per-ask exact answer is `project`'s. Its
    lattices stay private — consumed by `quantize`, the holdings query, and read-back; never exposed
    as a node `domain`. `quantize` authors the refill fetch-order (ADR-0006).
    """

    def quantize(self, request: Domain) -> SelectionDomain: ...


@dataclass(frozen=True)
class _Holding:
    """The atom of retention: one parameter's whole holding at one store cell.

    The Holding's window *is* `domain.axis(T).extent` — no second window field to drift. Private to
    this module, like the lattices (ADR-0006).
    """

    domain: GridDomain  # the record's native geometry for this parameter (deferred axes whole)
    data: ParameterData
    definition: ParameterDef
    provenance: Provenance  # the parameter's summary — origin, fetched_at, expiration


type _HoldingKey = tuple[ParameterId, int, int, EnumerableAxis]
"""`(parameter, x_index, y_index, z_key)` — lattice indices of the containing cell plus the record's
Z axis value object (frozen, hashable, equal across fetches of the same tap). One key shape serves
both wired positions."""


class MemoryStore:
    """The Holding-granular in-memory store: what it holds, it holds in whole assimilable Holdings.

    Substrate-named — the Holding fold is shape-generic (`deferred` parameterizes which axes a Holding
    spans wholly), and what distinguishes this store from persisting siblings is its memory backing,
    not its timeline. The lattices arrive *prepared*: the factory owns `StoreSpec` → lattice
    derivation, so no axis role is hardcoded here and a grid-style (T-latticed) instantiation is
    directly constructible (ADR-0006).
    """

    def __init__(
        self,
        grids: Mapping[AxisName, RegularAxis],
        deferred: frozenset[AxisName],
        clock: Clock,
        retention: timedelta,
    ) -> None:
        self._grids = grids
        self._deferred = deferred
        self._clock = clock
        self._retention = retention
        self._holdings: dict[_HoldingKey, _Holding] = {}

    async def project(self, selection: Selection) -> CoverageSet:
        """The holdings query: what I hold at the asked cells, as a `CoverageSet`.

        Translates the raw ask onto my boxes via the same `quantize` fold that authors a refill, so
        a request and its fetch-order select the same Holdings. Asked-but-unheld parameters are omitted;
        a cold store answers empty; stale Holdings return as data. This face is freshness-blind; the
        clock is eviction-only.
        """
        self._evict()
        boxes = self.quantize(selection.domain)
        x = self._box_indices(AxisName.X, boxes)
        y = self._box_indices(AxisName.Y, boxes)
        z_member = None if AxisName.Z in self._deferred else boxes.axis(AxisName.Z)
        # Identity-Z positions pass an enumerable cell through; ANY-Z is the deferred arm above.
        assert z_member is None or isinstance(z_member, EnumerableAxis)
        records: list[CoverageRecord] = []
        for pid in selection.parameters:
            matched = self._holdings_at(pid, x, y, z_member)
            # One parameter → one Holding under a point ask. Plural means a span-shaped ask or a
            # source declaring one parameter at two Z cells under ANY-Z — the Reservoir's side.
            assert len(matched) <= 1, (
                f"{pid!r} matched {len(matched)} Holdings under one ask — span-shaped ask or "
                f"multi-Z source under ANY-Z; neither is the store's to project"
            )
            if matched:
                records.append(self._as_record(pid, matched[0]))
        return CoverageSet(records=tuple(records))

    async def assimilate(self, answer: CoverageSet) -> None:
        """Absorb the natural answer, slicing it per parameter into whole Holdings.

        Only the store holds both halves of a Holding's identity — the containing cell from its
        private lattice, the native Z from the answer — so the slicing happens here, never in the
        `Reservoir`. A Holding is replaced whole (insert-or-overwrite, never merged), so it carries
        one origin and one window: a spliced `valid_time` is unrepresentable.
        """
        self._evict()
        for record in answer.records:
            domain = record.domain
            assert isinstance(domain, GridDomain)  # v1's one enumerable realization (#31 posture)
            x = self._containing_index(AxisName.X, domain)
            y = self._containing_index(AxisName.Y, domain)
            z_key = domain.axis(AxisName.Z)
            for pid, data in record.ranges.items():
                self._holdings[(pid, x, y, z_key)] = _Holding(
                    domain=domain,
                    data=data,
                    definition=record.capability.parameters[pid],
                    provenance=record.provenance.summary(pid),
                )

    @property
    def capability(self) -> Capability:
        """Holdings narration (#47): honest membership; reach truncates plural cells to the
        latest-assimilated Holding's domain. Interim — unused on the request path (the gate reads
        `project`'s returned `CoverageSet.capability`); recomputed on read until a multi-reach
        reader forces a maintained sparse form.
        """
        latest: dict[ParameterId, _Holding] = {}
        for holding in self._holdings.values():
            held = latest.get(holding.definition.id)
            # Strictly-newer replacement: ties keep the first-assimilated — arbitrary but stable.
            if held is None or holding.provenance.fetched_at > held.provenance.fetched_at:
                latest[holding.definition.id] = holding
        return GranularCapability(
            reaches={pid: (holding.definition, holding.domain) for pid, holding in latest.items()}
        )

    def quantize(self, request: Domain) -> SelectionDomain:
        """The fetch-order that fills my boxes for `request` — read `ground` first.

        `ground`'s store-side sibling: the same per-axis fold, enclosing where `ground` restricts.
        Its context is constructor state — the lattices and the axes a box spans wholly — never
        arguments.
        """
        separable = as_separable(request)
        if separable is None:
            raise ValueError("quantize needs per-axis geometry; the request is not separable")
        axes: dict[AxisName, SelectableAxis] = {}
        for name in AXIS_ORDER:
            member = separable.axis(name)
            if name in self._deferred:  # a box spans this axis wholly
                axes[name] = SnappedAxis(name, None)  #   → ANY, overriding the ask
            elif (grid := self._grids.get(name)) is not None:  # a box is one cell wide
                cells = grid.clip(member.extent)  #   containing cell(s); clip owns the math
                if cells is None:
                    raise ValueError(f"request {name.value} is outside the store lattice")
                axes[name] = replace(cells, cellular=False)  #   → the cells' *ticks*, honest points
            else:  # a box is keyed by the ask
                assert isinstance(member, RegularAxis | VantageAxis | SnappedAxis)  # SelectableAxis
                axes[name] = member
        return SelectionDomain(axes=axes)

    def _containing_index(self, name: AxisName, domain: GridDomain) -> int:
        """The store-lattice index of the cell containing the record's point — the same
        containing-cell math as `quantize` (`clip`), no parallel arithmetic."""
        grid = self._grids[name]
        axis = domain.axis(name)
        assert len(axis) == 1  # v1 records are point-shaped on X/Y; a gridded provider splits first
        point = axis[0].coordinate
        cell = grid.clip(Interval(point, point))  # type: ignore[arg-type]
        if cell is None:
            raise ValueError(f"record {name.value} is outside the store lattice")
        offset = sub_lattice_offset(grid, cell)
        assert offset is not None  # a clip result sits on its own lattice by construction
        return offset

    def _box_indices(self, name: AxisName, boxes: SelectionDomain) -> frozenset[int] | None:
        """Lattice indices the ask names on `name`, or `None` when a box spans the axis wholly."""
        if name in self._deferred:
            return None
        member = boxes.axis(name)
        assert isinstance(member, RegularAxis)  # latticed arm emits tick RegularAxes
        grid = self._grids[name]
        indices: set[int] = set()
        for i in range(len(member)):
            tick = member[i].coordinate
            cell = grid.clip(Interval(tick, tick))  # type: ignore[arg-type]
            assert cell is not None  # quantize already refused outside-lattice asks
            offset = sub_lattice_offset(grid, cell)
            assert offset is not None  # a clip result sits on its own lattice by construction
            indices.add(offset)
        return frozenset(indices)

    def _holdings_at(
        self,
        pid: ParameterId,
        x: frozenset[int] | None,
        y: frozenset[int] | None,
        z_key: EnumerableAxis | None,
    ) -> list[_Holding]:
        """What I hold for `pid` at the translated boxes — deferred axes constrain nothing."""
        return [
            holding
            for (held_pid, xi, yi, held_z), holding in self._holdings.items()
            if held_pid == pid
            and (x is None or xi in x)
            and (y is None or yi in y)
            and (z_key is None or held_z == z_key)
        ]

    @staticmethod
    def _as_record(pid: ParameterId, holding: _Holding) -> CoverageRecord:
        """One Holding as its own record — native domain, provenance intact (stale included)."""
        return CoverageRecord(
            capability=EnumerableCapability(
                domain=holding.domain, parameters={pid: holding.definition}
            ),
            ranges={pid: holding.data},
            provenance=Uniform(holding.provenance),
        )

    def _evict(self) -> None:
        """Drop Holdings past the retention window — substrate-private; the Store contract stays
        clockless for freshness. Eviction only removes; it never reshapes surviving Holdings."""
        cutoff = self._clock.now() - self._retention
        expired = [
            key for key, holding in self._holdings.items() if holding.provenance.fetched_at < cutoff
        ]
        for key in expired:
            del self._holdings[key]


class StoreFactory:
    """Allocates `MemoryStore`s: interprets `StoreSpec` into prepared lattices, validates the
    step, and passes through the wiring-declared `deferred` axes (ADR-0006).
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def create(self, spec: StoreSpec, deferred: frozenset[AxisName]) -> Store:
        if not 0 < spec.spatial_step <= 90:
            raise CompositionError(
                f"store spatial_step must be in (0, 90], got {spec.spatial_step}"
            )
        grids = {
            AxisName.X: _global_spatial(AxisName.X, spec.spatial_step),
            AxisName.Y: _global_spatial(AxisName.Y, spec.spatial_step),
        }
        return MemoryStore(grids, deferred, self._clock, spec.retention_interval)


def _global_spatial(name: AxisName, step: float) -> RegularAxis:
    """One cellular whole-globe lattice — cells cover the closed domain; the last may overhang.

    The overhang is inert (the MCP edge validates coordinates into range, so +90/+180 land in the
    last cell). No wraparound in v1: -180 and +180 are distinct cells, so the same meridian may be
    held twice.
    """
    anchor, span = (-180.0, 360.0) if name is AxisName.X else (-90.0, 180.0)
    return RegularAxis(name, anchor, step, floor(span / step) + 1, cellular=True)
