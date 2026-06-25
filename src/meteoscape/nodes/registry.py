"""`Registry` - the provider leaf-factory.

Handed plain config values, it owns the provider-id -> Provider-class catalog and instantiates the
enabled Providers (secrets injected), handing the raw leaves to the Weaver. No wiring, no `Store`s.
Instantiation behaviour is built from 001 onward.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .providers.base import Provider


class Registry:
    def __init__(self, catalog: Mapping[str, type[Provider]]) -> None:
        self.catalog = catalog

    def build(self, enabled: Sequence[str], secrets: Mapping[str, str]) -> Sequence[Provider]:
        raise NotImplementedError
