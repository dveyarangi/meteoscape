"""`Gateway` - the surface-neutral caller-policy boundary.

Applies caller policy (authz, rate-limit, quota - null / pass-through in v1) then calls `project` on
the best view. Not a Manifold itself: it can reject / throttle, it does not project. Served profiles
always materialize a Coverage; a non-Coverage result is a bug (non-taxonomy error).
"""

from __future__ import annotations

from ..manifold.core import Coverage, Manifold, Selection


class Gateway:
    def __init__(self, best_view: Manifold) -> None:
        self.best_view = best_view

    async def resolve(self, selection: Selection) -> Coverage:
        result = await self.best_view.project(selection)
        if not isinstance(result, Coverage):
            raise TypeError(f"best view must project to Coverage, got {type(result).__name__}")
        return result
