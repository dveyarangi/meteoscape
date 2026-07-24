"""Build-time binders and their products — the seam between `ProfileConfig` and the `Weaver`.

Two symmetrical binders resolve operator declarations against process-wide catalogues into read-only
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
from ..errors import CompositionError  # re-exported from `errors` (also raised in `manifold/`)
from ..identity import CalculatorKey, SourceKey
from ..manifold.capability import EnumerableCapability
from ..parameters import ParameterDef, ParameterId
from .catalog.calculators import CalculatorCatalog, CalculatorManifest
from .catalog.paramtable import ParameterTable
from .catalog.providers import ProviderCatalog
from .providers.base import Provider


@dataclass(frozen=True)
class RegisteredSource:
    """One configured producer plus extrinsic priority and optional Source-store knobs.

    Invariant: materialized (`EnumerableCapability`) ⇒ `store is None`; non-materialized ⇒ `store`
    set. Both enforced by the `SourceBinder`, so downstream reads `store is None` as the materialized
    fact without re-deriving it.
    """

    provider: Provider
    priority: int
    store: StoreSpec | None


def _is_materialized(provider: Provider) -> bool:
    """Every parameter on one enumerable domain ⇒ an already-materialized dataset (ADR-0006 / m2;
    the isinstance test is the v1 discriminator — m2 open question 2)."""
    return isinstance(provider.capability, EnumerableCapability)


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

            store: StoreSpec | None = offering.store if offering.store is not None else spec.store
            if _is_materialized(provider):
                if store is not None:
                    raise CompositionError(
                        f"store configured for materialized source {key}; "
                        "a materialized provider wires storeless"
                    )
            elif store is None:
                raise CompositionError(f"missing store shape for non-materialized source {key}")

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
    """Resolves `CalculatorDef` declarations into a `CalculatorRegistry`."""

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


def validate_calculators(profile: ProfileDef) -> None:
    """Every calculator input producible and the calculator graph acyclic; raise `CompositionError`.

    `weave`'s first step — its precondition, and the guard an operator's error surfaces from, so it
    must reject exactly what the Weaver cannot build. It therefore descends into every upstream
    calculator **even when a source also serves that input**: the Weaver builds a scoped Arbiter over
    *all* producers of an input, so a calculator cycle a source happens to shadow is still an
    unbuildable graph.
    """
    calculators = profile.calculators.calculators
    path: list[CalculatorKey] = []
    visiting: set[CalculatorKey] = set()
    done: set[CalculatorKey] = set()

    def source_serves(pid: ParameterId) -> bool:
        return any(
            pid in registered.provider.capability.parameters
            for registered in profile.sources.sources.values()
        )

    def ensure(key: CalculatorKey) -> None:
        if key in done:
            return
        if key in visiting:
            cycle = [*path[path.index(key) :], key]
            raise CompositionError("calculator cycle: " + " -> ".join(str(k) for k in cycle))
        visiting.add(key)
        path.append(key)
        for inp in calculators[key].inputs:
            upstream = [
                other for other, other_reg in calculators.items() if inp in other_reg.outputs
            ]
            if not upstream and not source_serves(inp):
                raise CompositionError(
                    f"calculator {key} input {inp} is not served by any producer"
                )
            for other in upstream:
                ensure(other)
        path.pop()
        visiting.discard(key)
        done.add(key)

    for key in calculators:
        ensure(key)
