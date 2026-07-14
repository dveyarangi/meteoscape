"""Private sampling engine behind `Coverage.project` — aligned crop only in v1.

Public face is `Coverage.project`; this module is the engine it delegates to. Kernel registry lands
at issue 007 when nearest-neighbor becomes the second kernel (ADR-0001: no separate `sample` verb).

Consumes any `Coverage` (protocol); always produces a `CoverageRecord` (session 0008).
"""

from __future__ import annotations

from ..parameters import ParameterId
from .capability import EnumerableCapability
from .core import Coverage, Selection
from .coverage import CoverageRecord
from .data import ParameterData
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


def _aligned_offsets(outer: GridDomain, inner: GridDomain) -> dict[AxisName, int] | None:
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
    ranges = {}
    for pid in selection.parameters:
        data = coverage.ranges[pid]
        values = [data.values[i] for i in source_indices]
        present = None if data.present is None else [data.present[i] for i in source_indices]
        ranges[pid] = ParameterData(values=values, present=present)

    return CoverageRecord(
        capability=EnumerableCapability(domain=target, parameters=parameters),
        ranges=ranges,
        provenance=_restrict_provenance(coverage.provenance, selection.parameters),
    )
