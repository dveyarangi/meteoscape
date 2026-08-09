"""Realized answers: the one-domain `Coverage` and the multi-domain carrier beside it (contracts in
`core.py`).

Realizations satisfy the contract *structurally*, not by inheritance: a frozen dataclass field would
clash with the protocol's `domain` property descriptor. `CoverageRecord` is v1's one memory-backed
realization (Timeline / Grid are domain *shapes*, not classes). `CoverageSet` has no single domain to
expose, so it is a `Manifold` and not a `Coverage` — projecting it is what yields one.

`sampling` imports `CoverageRecord` to build its result, so every `project` here reaches the engine
through a function-local import. Hoisting one to module scope breaks the package.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from ..errors import CapabilityMismatch
from ..parameters import ParameterDef, ParameterId
from .capability import Capability, EnumerableCapability, GranularCapability
from .core import Manifold, Selection
from .data import ParameterData
from .domain import Domain, EnumerableDomain
from .provenance import PerParameter, ProvenanceField


@dataclass(frozen=True)
class CoverageRecord:
    """The canonical memory-backed `Coverage`: inert value object over an enumerable `domain`.

    `capability` is the materialized `EnumerableCapability` - it carries the parameter set co-domained on
    its one enumerable grid, so the `Countable.domain` derives from `capability.domain` rather than being
    stored twice. `ranges` are positional to `domain`. Alternative implementations may vary by
    backing, never by domain shape.
    """

    capability: EnumerableCapability
    ranges: Mapping[ParameterId, ParameterData]
    provenance: ProvenanceField

    @property
    def domain(self) -> EnumerableDomain:
        return self.capability.domain

    async def project(self, selection: Selection) -> Manifold:
        from .sampling import resample

        return resample(self, selection)


@dataclass(frozen=True)
class CoverageSet:
    """The multi-domain answer: single-domain records the request's boundless axes let differ.

    A Manifold — project it with a fully enumerable Selection to fold onto one Coverage. What it
    advertises is `GranularCapability`: each parameter reaches the native geometry it arrived on.
    """

    records: tuple[CoverageRecord, ...]
    _capability: Capability = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """One pass: the disjointness invariant, and the capability it makes well-defined.

        A parameter on two records would leave "the owning record" — whose geometry `reach` answers
        and whose values the fold takes — ambiguous, so the set is refused instead of served.
        """
        reaches: dict[ParameterId, tuple[ParameterDef, Domain]] = {}
        for record in self.records:
            shared = reaches.keys() & record.ranges.keys()
            if shared:
                raise ValueError(f"a parameter lives on one record only: {sorted(shared)}")
            for pid in record.ranges:
                reaches[pid] = (record.capability.parameters[pid], record.domain)
        object.__setattr__(self, "_capability", GranularCapability(reaches=reaches))

    @classmethod
    def of(cls, answer: CoverageRecord | CoverageSet) -> CoverageSet:
        """Normalize a child answer for `assimilate` — identity on a group, wrap a record.

        The Reservoir is the only caller: a source child answers a `CoverageSet`; an Arbiter or
        Calculator answers a `CoverageRecord`. Anything else is an engine fault at the caller.
        """
        if isinstance(answer, CoverageSet):
            return answer
        return cls(records=(answer,))

    @property
    def capability(self) -> Capability:
        return self._capability

    async def project(self, selection: Selection) -> Manifold:
        """Fold onto `selection`: crop each owning record onto the ask, then merge.

        Each parameter is cropped against **its own** record's lattice, so records that differ are
        folded honestly rather than stacked on the first record's cells.

        Cropping a native cell onto the asked one relabels it — a 2 m value answering at the vantage
        the request named. That is honest only because admission gated each parameter against its own
        native footprint before this answer existed.

        A record the ask names nothing on is skipped, so asking for one parameter is never gated by
        the shape of a record it does not live on. The ask must name at least one parameter; nothing
        that can reach here authors an empty one.
        """
        from .sampling import resample

        target = selection.domain
        if not isinstance(target, EnumerableDomain):
            raise CapabilityMismatch("a coverage set folds onto an enumerable Selection only")
        unheld = selection.parameters - self._capability.parameters.keys()
        if unheld:
            raise CapabilityMismatch(f"coverage set does not hold {sorted(unheld)}")
        cropped = [
            resample(record, selection.with_params(wanted))
            for record in self.records
            if (wanted := selection.parameters & record.ranges.keys())
        ]
        return cropped[0] if len(cropped) == 1 else _merged(cropped, target)


def _merged(cropped: Sequence[CoverageRecord], domain: EnumerableDomain) -> CoverageRecord:
    """The cropped records as one Coverage — every parameter now on the shared target lattice."""
    ranges: dict[ParameterId, ParameterData] = {}
    parameters: dict[ParameterId, ParameterDef] = {}
    for record in cropped:
        ranges.update(record.ranges)
        parameters.update(record.capability.parameters)
    return CoverageRecord(
        capability=EnumerableCapability(domain=domain, parameters=parameters),
        ranges=ranges,
        provenance=_plane(cropped),
    )


def _plane(cropped: Sequence[CoverageRecord]) -> ProvenanceField:
    """The merged provenance: the shared plane when the records were stamped alike, else per owner.

    One fetch stamps every record with one plane, and keeping it is what lets a single-origin answer
    stay `Uniform` on the wire; records from separate fetches each own their parameters' origin.
    """
    shared = cropped[0].provenance
    if all(record.provenance == shared for record in cropped):
        return shared
    return PerParameter(
        {pid: record.provenance.summary(pid) for record in cropped for pid in record.ranges}
    )
