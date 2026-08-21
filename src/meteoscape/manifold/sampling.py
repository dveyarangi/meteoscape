"""Private sampling engine behind `Coverage.project` — aligned crop only in v1.

Public face is `Coverage.project`; this module is the engine it delegates to. A planned Resampler
registry varies the transfer without introducing a separate `sample` verb.

Consumes any `Coverage` protocol implementation and produces a `CoverageRecord`.
"""

from __future__ import annotations

from ..parameters import ParameterId
from .capability import EnumerableCapability
from .core import Coverage, Selection
from .coverage import CoverageRecord
from .domain import (
    AXIS_ORDER,
    AxisName,
    EnumerableDomain,
    GridDomain,
    RegularAxis,
    decode_flat_index,
    encode_flat_index,
    sub_lattice_offset,
)
from .provenance import PerParameter, PerPoint, ProvenanceField, Uniform


class Shortfall(ValueError):
    """The crop target runs past the source's end — aligned, and short by a known count.

    Distinct from a crop index arithmetic cannot express (off-phase, or a different step): here the
    overlap is well-defined and the missing tail is countable, which is what lets a caller diagnose a
    producer that delivered less than it declared.

    **TODO (temporary):** raising at all is scaffolding. `missing` is the durable part, because the
    answer to a shortfall is to pad that tail as `present=False` rather than to fail — which retires
    this class's raise and every translation of it
    (docs/concerns.md#30-response-membership-under-runtime-degraded-fallback).
    """

    def __init__(self, axis: AxisName, missing: int) -> None:
        super().__init__(f"crop target runs {missing} cell(s) past the source on {axis.value}")
        self.axis = axis
        self.missing = missing


def _aligned_offsets(outer: GridDomain, inner: GridDomain) -> dict[AxisName, int] | None:
    """Per-axis start index of `inner` within `outer` — `None` when no index arithmetic expresses it.

    `Shortfall` when the two agree on phase but `outer` ends first: a different failure, reported
    rather than collapsed into the unimplementable one.
    """
    offsets: dict[AxisName, int] = {}
    for name in AXIS_ORDER:
        outer_axis = outer.axes[name]
        inner_axis = inner.axes[name]
        if not isinstance(outer_axis, RegularAxis) or not isinstance(inner_axis, RegularAxis):
            # IntervalAxis / VantageAxis — identity crop when both are count-1 and equal length.
            if len(outer_axis) != len(inner_axis):
                return None
            offsets[name] = 0
            continue
        offset = sub_lattice_offset(outer_axis, inner_axis)
        if offset is None:
            return None
        missing = offset + inner_axis.count - outer_axis.count
        if missing > 0:
            raise Shortfall(name, missing)
        offsets[name] = offset
    return offsets


def _restrict_provenance(
    provenance: ProvenanceField, parameters: frozenset[ParameterId]
) -> ProvenanceField:
    """Keep capability / ranges / provenance on one parameter key set (core.py invariant)."""
    if isinstance(provenance, Uniform):
        return provenance
    if isinstance(provenance, PerParameter):
        return PerParameter({pid: provenance.by_parameter[pid] for pid in parameters})
    if isinstance(provenance, PerPoint):
        # TODO(#39): unbuilt, surfaced uncategorized — see the class inventory in concern #39.
        raise NotImplementedError(
            "PerPoint provenance must be re-indexed on a geometry crop — not built in v1"
        )
    raise TypeError(f"unknown ProvenanceField: {type(provenance)!r}")


def resample(coverage: Coverage, selection: Selection) -> CoverageRecord:
    """Project `coverage` onto `selection` — v1: parameter restrict + aligned enumerable crop."""
    held = coverage.capability.parameters
    missing = selection.parameters - held.keys()
    if missing:
        raise ValueError(f"parameter(s) not held: {sorted(missing)}")

    # TODO(#39): the three `NotImplementedError`s below are *unbuilt*, not producer faults, and
    # reach the surface uncategorized; #21 owns the capability over-promise behind this path.
    if not isinstance(selection.domain, EnumerableDomain):
        raise NotImplementedError("continuous selection requires Reservoir homogenization")

    if not isinstance(selection.domain, GridDomain) or not isinstance(coverage.domain, GridDomain):
        raise NotImplementedError("v1 sampling engine only crops GridDomain lattices")

    target: GridDomain = selection.domain
    source: GridDomain = coverage.domain
    offsets = _aligned_offsets(source, target)
    if offsets is None:
        raise NotImplementedError(
            "non-identical step or off-phase selection requires Reservoir homogenization"
        )

    source_counts = {name: len(source.axes[name]) for name in AXIS_ORDER}
    target_counts = {name: len(target.axes[name]) for name in AXIS_ORDER}

    source_indices: list[int] = []
    for j in range(len(target)):
        locals_ = decode_flat_index(target_counts, j)
        mapped = {name: offsets[name] + locals_[name] for name in AXIS_ORDER}
        source_indices.append(encode_flat_index(source_counts, mapped))

    parameters = {pid: held[pid] for pid in selection.parameters}
    ranges = {pid: coverage.ranges[pid].take(source_indices) for pid in selection.parameters}

    return CoverageRecord(
        capability=EnumerableCapability(domain=target, parameters=parameters),
        ranges=ranges,
        provenance=_restrict_provenance(coverage.provenance, selection.parameters),
    )
