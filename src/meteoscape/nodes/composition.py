"""Build-time binders and their products — the seam between `ProfileConfig` and the `Weaver`.

Two symmetrical binders resolve operator tickets against process-wide catalogues into read-only
registries, which compose the `ProfileDef` the Weaver consumes:

- `SourceBinder(ProviderCatalog).build(...)` → `SourceRegistry` (`SourceKey` → configured producer +
  extrinsic priority + Source-store lattice).
- `CalculatorBinder(CalculatorCatalog).build(...)` → `CalculatorRegistry` (output `ParameterId` →
  catalog-resolved binding, *not* a Calculator node — the Weaver builds those).

Binders instantiate/resolve; neither wires the DAG nor allocates the profile-root `Store` (the Weaver
owns that). Both take plain values by injection, never the `config.py` `Settings` type. See
architecture.md ("Config, binders, Weaver") and ADR-0005.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..clock import Clock
from ..config import ArbiterPolicy, CalculatorSpec, OfferingDef, RootStoreSpec
from ..identity import SourceKey
from ..manifold.core import Countable
from ..manifold.domain import EnumerableDomain
from ..parameters import ParameterId
from .catalog.calculators import CalculatorCatalog, CalculatorManifest
from .catalog.paramtable import ParameterTable
from .catalog.providers import ProviderCatalog
from .providers.base import Provider


class CompositionError(Exception):
    """Build-time failure — unknown ticket, dangling secret, duplicate key, unresolvable lattice."""


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
        defs: Sequence[OfferingDef],
        secrets: Mapping[str, str],
        clock: Clock,
        parameters: ParameterTable,
    ) -> SourceRegistry:
        """Instantiate producers per `OfferingDef`; derive `SourceKey` and resolve each source lattice."""
        sources: dict[SourceKey, RegisteredSource] = {}
        for offering in defs:
            if offering.name is None:
                raise NotImplementedError("OfferingDef expand (name=None) is not built yet")

            manifest = self.catalog.get(offering.impl)
            if manifest is None:
                raise CompositionError(f"unknown provider impl {offering.impl!r}")

            spec = manifest.offerings.get(offering.name)
            if spec is None:
                raise CompositionError(
                    f"unknown offering {offering.name!r} for impl {offering.impl!r}"
                )

            secret_value: str | None = None
            if offering.secret_ref is not None:
                if offering.secret_ref not in secrets:
                    raise CompositionError(f"dangling secret_ref {offering.secret_ref!r}")
                secret_value = secrets[offering.secret_ref]

            provider = manifest.build(spec, offering.settings, secret_value, clock, parameters)
            key = SourceKey(provider=manifest.provider_id, dataset=spec.name)
            if key in sources:
                raise CompositionError(f"duplicate SourceKey {key}")

            if isinstance(provider, Countable):
                lattice = provider.domain
            elif spec.default_lattice is not None:
                lattice = spec.default_lattice
            else:
                raise CompositionError(f"unresolvable source lattice for {key}")

            sources[key] = RegisteredSource(
                provider=provider,
                priority=offering.priority,
                source_lattice=lattice,
            )
        return SourceRegistry(sources=sources)


@dataclass(frozen=True)
class RegisteredCalculator:
    """Catalog-resolved calculator binding — not a Calculator node (Weaver builds those)."""

    output: ParameterId
    inputs: frozenset[ParameterId]
    manifest: CalculatorManifest
    stored: bool = False


@dataclass(frozen=True)
class CalculatorRegistry:
    """Read-only, output-keyed surface the Weaver consumes — resolved calculator bindings."""

    calculators: Mapping[ParameterId, RegisteredCalculator]


class CalculatorBinder:
    """Resolves `CalculatorSpec` tickets against a `CalculatorCatalog` → `CalculatorRegistry`."""

    def __init__(self, catalog: CalculatorCatalog) -> None:
        self.catalog = catalog

    def build(self, specs: Sequence[CalculatorSpec]) -> CalculatorRegistry:
        """Lookup each `fn_id`; fail unknown ids; return bindings keyed by output parameter."""
        calculators: dict[ParameterId, RegisteredCalculator] = {}
        for spec in specs:
            manifest = self.catalog.get(spec.fn_id)
            if manifest is None:
                raise CompositionError(f"unknown calculator fn_id {spec.fn_id!r}")
            calculators[spec.output] = RegisteredCalculator(
                output=spec.output,
                inputs=spec.inputs,
                manifest=manifest,
                stored=spec.stored,
            )
        return CalculatorRegistry(calculators=calculators)


@dataclass(frozen=True)
class ProfileDef:
    """Weave input — two resolved registries + profile knobs (not a freeform DAG)."""

    sources: SourceRegistry
    calculators: CalculatorRegistry
    root_store: RootStoreSpec
    arbiter: ArbiterPolicy
