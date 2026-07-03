"""Concrete `Coverage` realizations (the contract itself lives in `core.py`).

Realizations satisfy the contract *structurally*, not by inheritance: a frozen dataclass field would
clash with the protocol's `domain` property descriptor. v1 ships `Timeline`; `Grid` (spatial output)
is a later slice.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..catalog.vocabulary import ParameterId
from .capability import Capability
from .core import Manifold, Selection
from .data import ParameterData
from .domain import EnumerableDomain
from .provenance import ProvenanceField


@dataclass(frozen=True)
class Timeline:
    """The v1 `Coverage`: a dense field over a `valid_time`-axis `domain` at a fixed location.

    Satisfies the `Coverage` contract structurally (no inheritance). `capability` carries the parameter
    set (co-domained on `domain`); `ranges` are positional to `domain`.
    """

    domain: EnumerableDomain
    capability: Capability
    ranges: Mapping[ParameterId, ParameterData]
    provenance: ProvenanceField

    def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError
