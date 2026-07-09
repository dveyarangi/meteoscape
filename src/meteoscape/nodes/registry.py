"""`Registry` - the producer leaf-factory.

Owns the static `impl-id → Provider class` catalog. Handed `SourceDef` recipes + secrets + a `Clock`,
it instantiates one configured producer per recipe and returns a read-only `SourceRegistry`
(`SourceKey` → provider + extrinsic `priority`). No wiring, no `Store`s — the Weaver consumes the
role. See architecture.md ("Config, Registry, Weaver").
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..clock import Clock
from ..config import SourceDef
from ..identity import SourceKey
from .providers.base import Provider


@dataclass(frozen=True)
class RegisteredSource:
    """One configured producer plus its extrinsic priority (policy, not a Provider field)."""

    provider: Provider
    priority: int


@runtime_checkable
class SourceRegistry(Protocol):
    """Read-only, `SourceKey`-keyed surface the Weaver consumes — producers + each one's priority."""

    @property
    def sources(self) -> Mapping[SourceKey, RegisteredSource]: ...


@dataclass(frozen=True)
class BuiltSourceRegistry:
    """Concrete `SourceRegistry` produced by `Registry.build`."""

    sources: Mapping[SourceKey, RegisteredSource]


class Registry:
    def __init__(self, catalog: Mapping[str, type[Provider]]) -> None:
        self.catalog = catalog

    def build(
        self, defs: Sequence[SourceDef], secrets: Mapping[str, str], clock: Clock
    ) -> SourceRegistry:
        """Instantiate one producer per `SourceDef`; secrets and clock injected at construction."""
        raise NotImplementedError
