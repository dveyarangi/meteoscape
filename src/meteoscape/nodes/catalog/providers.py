"""Provider plugin catalogue: offerings, secrets, and the build/expand face.

`ProviderCatalog` is `impl_id → ProviderManifest`. An `OfferingSpec` is a product row (exact
parameter IDs + optional default lattice); `SourceDef` only enables it. See ADR-0005.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from ...parameters import ParameterId
from ...clock import Clock
from ...manifold.domain import EnumerableDomain
from ..providers.base import Provider
from .paramtable import ParameterTable

ProviderCatalog = Mapping[str, "ProviderManifest"]


@dataclass(frozen=True)
class SecretSlot:
    """Impl-level secret binding name — offerings inherit; values live in the injected secrets map."""

    name: str


@dataclass(frozen=True)
class OfferingSpec:
    """Catalogue product row — name → `SourceKey.dataset`; exact params; optional non-Countable lattice."""

    name: str
    parameters: frozenset[ParameterId]
    default_lattice: EnumerableDomain | None = None


@dataclass(frozen=True)
class ProviderManifest:
    """Plugin face for one impl — declared offerings, secret slot, `build` / optional `expand`."""

    impl_id: str
    provider_id: str
    offerings: Mapping[str, OfferingSpec]
    secret: SecretSlot | None
    build: Callable[
        [OfferingSpec, Mapping[str, object], str | None, Clock, ParameterTable],
        Provider,
    ]
    expand: (
        Callable[
            [Mapping[str, object], str | None, Clock, ParameterTable],
            Sequence[Provider],
        ]
        | None
    ) = None
