"""Concrete `Coverage` realizations.

The `Coverage` *contract* (the materialized leaf) lives with the algebra in `core.py`, because
`Writable` consumes it and `Coverage <: Manifold` - co-locating them keeps the algebra acyclic. This
module holds the realizations that satisfy that contract *structurally* (no inheritance: a frozen
dataclass field would clash with the protocol's `domain` property descriptor). v1 ships `Timeline`;
`Grid` (spatial output) is added in its own slice.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .core import Manifold, Selection
from .domain import EnumerableDomain
from .parameters.data import ParameterData
from .parameters.vocabulary import ParameterId


@dataclass(frozen=True)
class Timeline:
    """The v1 `Coverage`: a dense field over a `valid_time`-axis `domain` at a fixed location.

    One `ParameterData` range per parameter, positional to `domain`. Satisfies `Coverage`
    structurally; the array backing of `values` stays private behind `ParameterData`. `project`
    behaviour is deferred to the slices that sample.
    """

    domain: EnumerableDomain
    ranges: Mapping[ParameterId, ParameterData]

    def project(self, selection: Selection) -> Manifold:
        raise NotImplementedError
