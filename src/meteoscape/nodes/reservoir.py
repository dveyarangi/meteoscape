"""`Reservoir` - the retention composite.

A read-only Manifold composed of a `Store` + one child. Adds retention, not selection. See
docs/architecture.md ("Reservoir") and ADR-0001. The `Store` protocol and factories live in
`store.py`.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..clock import Clock
from ..errors import CapabilityMismatch, RuntimeFailure
from ..manifold.capability import Capability, EnumerableCapability
from ..manifold.core import Manifold, Selection
from ..manifold.coverage import CoverageRecord, CoverageSet
from ..manifold.domain import (
    Axis,
    AxisName,
    Domain,
    EnumerableAxis,
    EnumerableDomain,
    GridDomain,
    agreed_geometry,
    as_enumerable_axes,
    as_separable,
    ground,
    open_axes,
)
from ..parameters import ParameterId
from .store import Store

_POINT_AXES = (AxisName.X, AxisName.Y, AxisName.Z)


class Reservoir:
    """A read-only Manifold composed of a `Store` + one child.

    The child is a Provider (the *source* role), an Arbiter (the *best view*), or an opt-in stored
    Calculator. The retention pipeline is identical; only the child and Store shape differ.

    Adds retention, not selection, so its `capability` forwards the source's unchanged (the `Store`
    grid is an internal fidelity floor, not a capability boundary). Freshness is this node's policy
    over holdings — the store face stays clockless (ADR-0006).

    TODO (temporary): docs/concerns.md#39-python-embedding-surface-and-public-failures
    will separate engine invariant breaks from producer `RuntimeFailure`s. The borrowed category is
    the only one that currently reaches every surface cleanly.
    """

    def __init__(self, store: Store, source: Manifold, clock: Clock) -> None:
        self.store = store
        self.source = source
        self._clock = clock

    # @hotpath
    async def project(self, selection: Selection) -> Manifold:
        """Load holdings → gate → refill missing/stale → assimilate → reload → read-back."""
        admitted = frozenset(
            pid
            for pid in selection.parameters
            if self.source.capability.serves(pid, selection.domain)
        )
        if not admitted:
            raise CapabilityMismatch("no producer admits any requested parameter")

        # The store takes the **raw** ask and translates onto its own boxes: stale Holdings come back
        # as data, unheld parameters are omitted, and an empty answer is a cold store, not an error.
        held = await self.store.project(selection)
        assert isinstance(held, CoverageSet)

        # Only admitted parameters may refill or serve; retained data outside current capability is
        # historical state, not an answer.
        missing = self._missing(admitted, held, selection)
        if missing:
            # `quantize` is the fetch-order — its one public use, so the lattices stay store-private.
            # The ask names only the missing parameters; a wider answer is the child's own natural
            # fetch unit to give (ask narrow, answer natural, store absorbs).
            shape = self.store.quantize(selection.domain)
            answer = await self.source.project(Selection(domain=shape, parameters=missing))
            await self.store.assimilate(self._as_group(answer))

            held = await self.store.project(selection)
            assert isinstance(held, CoverageSet)
            if not held.capability.parameters:
                # The child answered nothing while raising nothing, or nothing landed: engine fault.
                raise RuntimeFailure("refill produced no holdings")

        # An ask the Holdings cannot meet is unservable, not missing — warm in-gap asks never
        # refill, so this check must sit on the shared path (ADR-0002).
        self._reject_unmeetable(admitted, held, selection)

        # Serving happens from the store alone, warm or refilled — one path, which is what makes a
        # shared `issue_time` across a mixed request structural rather than a test's good luck.
        return await self._read_back(held, selection, admitted)

    @property
    def capability(self) -> Capability:
        return self.source.capability

    def _missing(
        self,
        admitted: frozenset[ParameterId],
        held: CoverageSet,
        selection: Selection,
    ) -> frozenset[ParameterId]:
        """Parameters that need a refill: absent, unsatisfied retention, or expired.

        `admitted` comes from the child's Capability, so a refill never widens the parameter ask.
        A wider answer is only the child's natural fetch unit. Under ANY on T a Holding is the whole
        of one fetch, so freshness alone governs coverage.
        """
        needed = None if AxisName.T in open_axes(selection.domain) else _t_axis(selection.domain)
        missing: set[ParameterId] = set()
        for pid in admitted:
            if pid not in held.capability.parameters:
                missing.add(pid)
                continue
            if needed is not None:
                # Invariant: serves already admitted this pair — no overlap is an engine break,
                # not "satisfied" via the predicate's want-is-None arm (ADR-0002).
                declared = _t_axis(self.source.capability.reach(pid))
                assert needed.matches(declared)
                if not declared.satisfied_by(_t_axis(held.capability.reach(pid)), needed):
                    missing.add(pid)
                    continue
            if _owning(held, pid).provenance.summary(pid).expiration <= self._clock.now():
                missing.add(pid)
        return frozenset(missing)

    def _reject_unmeetable(
        self,
        admitted: frozenset[ParameterId],
        held: CoverageSet,
        selection: Selection,
    ) -> None:
        """Holdings that do not meet the ask are a capability miss, not a ground-time fault.

        Runs after any refill, so it asks whether what we *now* hold can answer — never whether a
        fetch would help, which is the retention predicate's question (ADR-0002).

        `matches` rather than a bare overlap test, because its per-kind dispatch is exactly what each
        request shape needs to be answerable: a snapped ask negotiates its bounds, so overlap is
        enough and `ground` clips the rest; an exact ask names cells nothing will clip, so the
        holdings must contain them or `resample`'s aligned crop fails uncategorized.
        """
        asked_t = _t_axis(selection.domain)
        for pid in admitted & held.capability.parameters.keys():
            held_t = _t_axis(held.capability.reach(pid))
            if not asked_t.matches(held_t):
                raise CapabilityMismatch(
                    f"holdings do not meet asked T for {pid}: "
                    f"asked {asked_t.extent}, held {held_t.extent}"
                )

    def _as_group(self, answer: Manifold) -> CoverageSet:
        if isinstance(answer, (CoverageRecord, CoverageSet)):
            return CoverageSet.of(answer)
        raise RuntimeFailure("child answered with a non-record Coverage; nothing to assimilate")

    async def _read_back(
        self,
        held: CoverageSet,
        selection: Selection,
        admitted: frozenset[ParameterId] | None = None,
    ) -> Manifold:
        """Serve the Holdings on the request-derived answer geometry — relabel, then fold.

        Relabel is the fact→product claim; the carrier fold is the arithmetic. Keeping them separate
        leaves that claim one reviewable home.

        **Serving is gated by admission, not by holdings alone.** A parameter the child's reach no
        longer covers was skipped by the refill, so what remains held for it is data nothing would
        refresh — serving it would answer outside the declared reach, and grounding it can fail the
        whole request. Unreachable while every parameter shares one T reach (v1's single provider);
        live at the first diverging-reach parameter set
        (docs/concerns.md#30-response-membership-under-runtime-degraded-fallback).
        """
        served = frozenset(held.capability.parameters)
        if admitted is not None:
            served &= admitted
        if not served:
            raise RuntimeFailure("no admitted parameter survived the refill")
        records = tuple(record for record in held.records if record.ranges.keys() & served)
        try:
            target = agreed_geometry(
                (ground(selection.domain, record.domain) for record in records),
                request=selection.domain,
            )
        except ValueError as exc:
            raise RuntimeFailure("Holdings cannot ground onto an admitted request") from exc
        relabelled = tuple(self._relabel_onto(record, target) for record in records)
        return await CoverageSet(relabelled).project(Selection(target, served))

    def _relabel_onto(self, record: CoverageRecord, target: EnumerableDomain) -> CoverageRecord:
        """Rewrite count-1 X/Y/Z onto `target`; values and provenance untouched.

        This method is the **claim** (this 2 m value answers your 0-10 m vantage) — honest only
        because admission gated it. The **transfer** is `resample`, reached through
        `CoverageSet.project`; v1's Resampler is **identity**, so no value moves here or there.
        Parameter-specific Resamplers that would change that live at
        docs/concerns.md#5-read-time-homogenization-fidelity.
        """
        held = _axes_of(record.domain)
        onto = _axes_of(target)
        for name in _POINT_AXES:
            assert len(held[name]) == 1, f"v1 read-back needs a point on {name.value}"
            assert len(onto[name]) == 1, f"v1 read-back needs a point on {name.value}"
        relabelled = GridDomain(
            axes={
                AxisName.X: onto[AxisName.X],
                AxisName.Y: onto[AxisName.Y],
                AxisName.Z: onto[AxisName.Z],
                AxisName.T: held[AxisName.T],
            }
        )
        return CoverageRecord(
            capability=EnumerableCapability(
                domain=relabelled, parameters=dict(record.capability.parameters)
            ),
            ranges=record.ranges,
            provenance=record.provenance,
        )


def _owning(held: CoverageSet, pid: ParameterId) -> CoverageRecord:
    for record in held.records:
        if pid in record.ranges:
            return record
    raise RuntimeFailure(f"holdings advertise {pid!r} with no owning record")


def _t_axis(domain: Domain) -> Axis:
    """The T member of a separable geometry — retention compares axes, not intervals."""
    separable = as_separable(domain)
    if separable is None:
        raise RuntimeFailure("T axis needs separable geometry")
    return separable.axis(AxisName.T)


def _axes_of(domain: EnumerableDomain) -> Mapping[AxisName, EnumerableAxis]:
    """Read-back's addressable axes — the geometry check is `domain.py`'s; the sentence is ours."""
    axes = as_enumerable_axes(domain)
    if axes is None:
        raise RuntimeFailure("read-back needs per-axis geometry with cells on every axis")
    return axes
