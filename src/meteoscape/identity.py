"""`SourceKey` - identity of a configured producer, a Tier-0 leaf.

Peer of `errors` / `clock`: self-contained, imported inward by config, registry, provenance, and
providers. Conceptually provenance-anchored (an atomic `Origin` is stamped with it); the type lives
here so config/registry never reach into `manifold/`. See ADR-0003.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceKey:
    """Identity of a configured producer - provider plus its named dataset/offering.

    Shared by config (a `SourceDef` is built from it) and data (an `AtomicOrigin` is stamped with it);
    its `str` form is the SourceRegistry / config token (e.g. `open-meteo:best_match`). Structured rather than a
    delimited string so a provider exposing several datasets/offerings extends additively. `dataset` is
    always named - a `SourceKey` is never a partial (provider-only) identity; the offering's default is
    impl-supplied at construction (v1 Open-Meteo -> `best_match`). See ADR-0003.
    """

    provider: str
    dataset: str

    def __str__(self) -> str:
        return f"{self.provider}:{self.dataset}"
