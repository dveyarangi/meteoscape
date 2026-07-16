"""Build-time binders and their products — the seam between `ProfileConfig` and the `Weaver`.

Two symmetrical binders resolve operator tickets against process-wide catalogues into read-only
registries, which compose the `ProfileDef` the Weaver consumes:

- `SourceBinder(ProviderCatalog).build(...)` → `SourceRegistry` (`SourceKey` → configured producer +
  extrinsic priority + optional Source `StoreSpec`).
- `CalculatorBinder(CalculatorCatalog).build(...)` → `CalculatorRegistry` (`CalculatorKey` →
  catalog-resolved binding with resolved output defs, *not* a Calculator node — the Weaver builds those).

Binders instantiate/resolve; neither wires the DAG nor allocates the profile-root `Store` (the Weaver
owns that). Both take plain values by injection, never the `config.py` `Settings` type. See
architecture.md ("Config, binders, Weaver") and ADR-0005.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..clock import Clock
from ..config import ArbiterPolicy, CalculatorDef, OfferingDef, StoreSpec
from ..identity import CalculatorKey, SourceKey
from ..manifold.core import Countable
from ..parameters import ParameterDef, ParameterId
from .catalog.calculators import CalculatorCatalog, CalculatorManifest
from .catalog.paramtable import ParameterTable
from .catalog.providers import ProviderCatalog
from .providers.base import Provider


class CompositionError(Exception):
    """Build-time failure — unknown ticket, dangling secret, duplicate key, missing StoreSpec."""


@dataclass(frozen=True)
class RegisteredSource:
    """One configured producer plus extrinsic priority and optional Source-store knobs.

    Invariant: Countable ⇒ `store is None`; non-Countable ⇒ `store` set.
    """

    provider: Provider
    priority: int
    store: StoreSpec | None


@dataclass(frozen=True)
class SourceRegistry:
    """Read-only, `SourceKey`-keyed surface the Weaver consumes — producers + priority + store."""

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
        """Instantiate producers per `OfferingDef`; derive `SourceKey` and resolve each Source store."""
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
                store: StoreSpec | None = None
            else:
                store = offering.store if offering.store is not None else spec.store
                if store is None:
                    raise CompositionError(f"missing store for non-Countable source {key}")

            sources[key] = RegisteredSource(
                provider=provider,
                priority=offering.priority,
                store=store,
            )
        return SourceRegistry(sources=sources)


@dataclass(frozen=True)
class RegisteredCalculator:
    """Catalog-resolved calculator binding — not a Calculator node (Weaver builds those)."""

    key: CalculatorKey
    outputs: Mapping[ParameterId, ParameterDef]
    inputs: frozenset[ParameterId]
    manifest: CalculatorManifest
    priority: int
    stored: bool = False


@dataclass(frozen=True)
class CalculatorRegistry:
    """Read-only, `CalculatorKey`-keyed surface the Weaver consumes — resolved calculator bindings."""

    calculators: Mapping[CalculatorKey, RegisteredCalculator]


class CalculatorBinder:
    """Resolves `CalculatorDef` tickets against a `CalculatorCatalog` → `CalculatorRegistry`."""

    def __init__(self, catalog: CalculatorCatalog) -> None:
        self.catalog = catalog

    def build(
        self, defs: Sequence[CalculatorDef], parameters: ParameterTable
    ) -> CalculatorRegistry:
        """Lookup each `fn_id`; resolve output defs; key by `CalculatorKey` (name defaults to default)."""
        calculators: dict[CalculatorKey, RegisteredCalculator] = {}
        for recipe in defs:
            manifest = self.catalog.get(recipe.fn_id)
            if manifest is None:
                raise CompositionError(f"unknown calculator fn_id {recipe.fn_id!r}")
            name = "default" if recipe.name is None else recipe.name
            key = CalculatorKey(method=recipe.fn_id, name=name)
            if key in calculators:
                raise CompositionError(f"duplicate CalculatorKey {key}")
            try:
                outputs = {pid: parameters.get(pid) for pid in recipe.outputs}
            except KeyError as exc:
                raise CompositionError(f"unknown calculator output {exc.args[0]!r}") from exc
            calculators[key] = RegisteredCalculator(
                key=key,
                outputs=outputs,
                inputs=recipe.inputs,
                manifest=manifest,
                priority=recipe.priority,
                stored=recipe.stored,
            )
        return CalculatorRegistry(calculators=calculators)


@dataclass(frozen=True)
class ProfileDef:
    """Weave input — two resolved registries + profile knobs (not a freeform DAG)."""

    sources: SourceRegistry
    calculators: CalculatorRegistry
    root_store: StoreSpec
    arbiter: ArbiterPolicy
