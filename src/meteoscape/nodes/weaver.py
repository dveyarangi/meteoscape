"""`Weaver` — the build-time graph constructor.

`weave(ProfileDef)` allocates every `Store`, wraps sources and calculators as `Producer`s, constructs
the `Reconciler` via `build_reconciler`, and builds `Arbiter(producers, reconciler)` under the
best-view `Reservoir`. Calculators are memoized per `CalculatorKey` with a scoped input Arbiter
(DAG). The Weaver never ranks — priority stays registry data the reconciler interprets. See
architecture.md ("Config, binders, Weaver") and ADR-0005 / ADR-0004.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..config import StoreSpec
from ..identity import CalculatorKey
from ..manifold.core import Countable, Manifold
from ..manifold.domain import EnumerableDomain
from ..parameters import ParameterId
from .arbiter import Arbiter, Producer, Reconciler, build_reconciler
from .calculator import Calculator
from .composition import CompositionError, ProfileDef, RegisteredSource
from .reservoir import Reservoir
from .store import StoreFactory


def _source_grid(registered: RegisteredSource) -> EnumerableDomain | StoreSpec:
    """Provider-exact domain when Countable; otherwise the Source `StoreSpec` knobs."""
    if registered.store is None:
        assert isinstance(registered.provider, Countable)
        return registered.provider.domain
    return registered.store


class Weaver:
    def __init__(self, stores: StoreFactory) -> None:
        self.stores = stores

    def weave(self, profile: ProfileDef) -> Manifold:
        """Wire source + calculator Producers → top Arbiter → best-view Reservoir.

        Declared `Manifold`, not the composite it builds. ADR-0005 fixes what the Weaver
        *constructs*; the return type is what it *promises*, and root retention is a config fact
        (`root_store`) — the same knob `stored` is for a Calculator below, which is why that node is
        `Manifold` too. What makes the root the best view is selection, and selection is the
        Arbiter's; the `Reservoir` only adds retention (ADR-0001).
        """
        source_producers = self._weave_providers(profile)
        reconciler = build_reconciler(profile.arbiter, profile.sources, profile.calculators)
        calc_producers = self._weave_calculators(profile, source_producers, reconciler)
        return Reservoir(
            self.stores.create(profile.root_store),
            Arbiter([*source_producers, *calc_producers], reconciler),
        )

    def _weave_providers(self, profile: ProfileDef) -> list[Producer]:
        """Wrap each registered Source as `Producer(Reservoir(store, Provider), SourceKey)`."""
        return [
            Producer(
                node=Reservoir(self.stores.create(_source_grid(registered)), registered.provider),
                key=key,
            )
            for key, registered in profile.sources.sources.items()
        ]

    def _weave_calculators(
        self,
        profile: ProfileDef,
        source_producers: Sequence[Producer],
        reconciler: Reconciler,
    ) -> list[Producer]:
        """Memoize one Calculator `Producer` per `CalculatorKey` (scoped input Arbiter; DAG)."""
        memo: dict[CalculatorKey, Producer] = {}
        visiting: set[CalculatorKey] = set()

        def producers_for(params: frozenset[ParameterId]) -> list[Producer]:
            for key, reg in profile.calculators.calculators.items():
                if params & reg.outputs.keys():
                    build_calc(key)
            return [
                p
                for p in (*source_producers, *memo.values())
                if params & p.node.capability.parameters.keys()
            ]

        def build_calc(key: CalculatorKey) -> Producer:
            if key in memo:
                return memo[key]
            if key in visiting:
                raise CompositionError(f"calculator cycle at {key}")
            visiting.add(key)
            reg = profile.calculators.calculators[key]
            scoped = Arbiter(producers_for(reg.inputs), reconciler)
            calc = Calculator(reg.outputs, reg.inputs, reg.manifest.fn, scoped)
            node: Manifold = (
                Reservoir(self.stores.create(profile.root_store), calc) if reg.stored else calc
            )
            producer = Producer(node=node, key=key)
            visiting.discard(key)
            memo[key] = producer
            return producer

        return [build_calc(key) for key in profile.calculators.calculators]
