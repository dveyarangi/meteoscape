"""Producer identities — `SourceKey` / `CalculatorKey`, Tier-0 leaves.

Peer of `errors` / `clock`: self-contained, imported inward by config, registry, provenance, and
providers. Conceptually provenance-anchored (an atomic `Origin` is stamped with a `SourceKey`); the
types live here so config/registry never reach into `manifold/`. See ADR-0003 / ADR-0005.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceKey:
    """Identity of a configured source — provider plus its named dataset/offering.

    Shared by config (an `OfferingDef` selects the offering that becomes it) and data (an `AtomicOrigin` is stamped with it);
    its `str` form is the SourceRegistry / config token (e.g. `open-meteo:best_match`). Structured rather than a
    delimited string so a provider exposing several datasets/offerings extends additively. `dataset` is
    always named - a `SourceKey` is never a partial (provider-only) identity; the offering's default is
    impl-supplied at construction (v1 Open-Meteo -> `best_match`). See ADR-0003.
    """

    provider: str
    dataset: str

    def __str__(self) -> str:
        return f"{self.provider}:{self.dataset}"


@dataclass(frozen=True)
class CalculatorKey:
    """Identity of a configured calculator — method plus named variant.

    Peer of `SourceKey`; keyed on the *method* (`fn_id`), not the output group, so two calculators
    serving the same outputs by different methods are distinct competing producers. `name` is the
    configured variant; the binder defaults it to `"default"` when a `CalculatorDef` omits it.
    See ADR-0005.
    """

    method: str
    name: str

    def __str__(self) -> str:
        return f"{self.method}:{self.name}"


ProducerKey = SourceKey | CalculatorKey
"""Union of source and calculator identities — the key arm of an Arbiter `Producer`."""
