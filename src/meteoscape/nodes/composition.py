"""Build-time binders and their products — the seam between `ProfileConfig` and the `Weaver`.

Two symmetrical binders resolve operator tickets against process-wide catalogues into read-only
registries, which compose the `ProfileDef` the Weaver consumes:

- `SourceBinder(ProviderCatalog).build(...)` → `SourceRegistry` (`SourceKey` → configured producer +
  extrinsic priority + Source-store lattice).
- `DerivationBinder(DerivationCatalog).build(...)` → `DerivationRegistry` (output `ParameterId` →
  catalog-resolved binding, *not* a Calculator — the Weaver builds those).

Binders instantiate/resolve; neither wires the DAG nor allocates the profile-root `Store` (the Weaver
owns that). Both take plain values by injection, never the `config.py` `Settings` type. See
architecture.md ("Config, binders, Weaver") and ADR-0005.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..clock import Clock
from ..config import ArbiterPolicy, DerivationSpec, RootStoreSpec, SourceDef
from ..identity import SourceKey
from ..manifold.domain import EnumerableDomain
from ..parameters import ParameterId
from .catalog.derivations import DerivationCatalog, DerivationManifest
from .catalog.paramtable import ParameterTable
from .catalog.providers import ProviderCatalog
from .providers.base import Provider


@dataclass(frozen=True)
class RegisteredSource:
    """One configured producer plus extrinsic priority and its Source-store lattice."""

    provider: Provider
    priority: int
    source_lattice: EnumerableDomain


@dataclass(frozen=True)
class SourceRegistry:
    """Read-only, `SourceKey`-keyed surface the Weaver consumes — producers + priority + lattice."""

    sources: Mapping[SourceKey, RegisteredSource]


class SourceBinder:
    def __init__(self, catalog: ProviderCatalog) -> None:
        self.catalog = catalog

    def build(
        self,
        defs: Sequence[SourceDef],
        secrets: Mapping[str, str],
        clock: Clock,
        parameters: ParameterTable,
    ) -> SourceRegistry:
        """Instantiate producers per `SourceDef`; derive `SourceKey` and resolve each source lattice."""
        raise NotImplementedError


@dataclass(frozen=True)
class RegisteredDerivation:
    """Catalog-resolved derivation binding — not a Calculator (Weaver builds those)."""

    output: ParameterId
    inputs: frozenset[ParameterId]
    manifest: DerivationManifest
    stored: bool = False


@dataclass(frozen=True)
class DerivationRegistry:
    """Read-only, output-keyed surface the Weaver consumes — resolved derivation bindings."""

    derivations: Mapping[ParameterId, RegisteredDerivation]


class DerivationBinder:
    """Resolves `DerivationSpec` tickets against a `DerivationCatalog` → `DerivationRegistry`."""

    def __init__(self, catalog: DerivationCatalog) -> None:
        self.catalog = catalog

    def build(self, specs: Sequence[DerivationSpec]) -> DerivationRegistry:
        """Lookup each `fn_id`; fail unknown ids; return bindings keyed by output parameter."""
        raise NotImplementedError


@dataclass(frozen=True)
class ProfileDef:
    """Weave input — two resolved registries + profile knobs (not a freeform DAG)."""

    sources: SourceRegistry
    derivations: DerivationRegistry
    root_store: RootStoreSpec
    arbiter: ArbiterPolicy
