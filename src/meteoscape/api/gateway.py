"""`Gateway` - the surface-neutral caller-policy boundary.

Applies caller policy (authz, rate-limit, quota - null / pass-through in v1) then calls `project` on
the best view. Not a Manifold itself: it can reject / throttle, it does not project.
"""

from __future__ import annotations

from ..manifold.core import Manifold, Selection


class Gateway:
    def __init__(self, best_view: Manifold) -> None:
        self.best_view = best_view

    async def resolve(self, selection: Selection) -> Manifold:
        raise NotImplementedError
