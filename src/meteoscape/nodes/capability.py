"""`Capability` - the producer -> Arbiter serving contract.

Structured clauses matched by one generic predicate (key equality / range containment /
kind-aware extent reachability). Ordering and the reconciler are policy, not Capability. The match
predicate's behaviour is deferred (matching logic is test-driven from 005 onward).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from ..manifold.domain import Domain
from ..manifold.parameters.vocabulary import CellAggregation, ParameterId, Quantity


@dataclass(frozen=True)
class Extent:
    """An extensive quantity's native extent. Declared seam: extensive matching is built later."""

    period: timedelta
    phase: timedelta


@dataclass(frozen=True)
class CapabilityClause:
    """One emitted parameter's serving clause: key + covered Domain (+ extent for extensive)."""

    quantity: Quantity
    aggregation: CellAggregation
    coverage: Domain
    extent: Extent | None = None


class Capability:
    """A producer's clauses + the generic `serves` predicate (behaviour deferred)."""

    def __init__(self, clauses: Sequence[CapabilityClause]) -> None:
        self.clauses = clauses

    def serves(self, parameter: ParameterId, domain: Domain) -> bool:
        raise NotImplementedError
