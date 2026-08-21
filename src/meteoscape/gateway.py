"""`Gateway` - the surface-neutral caller-policy boundary, and the composition it fronts.

Applies caller policy (authz, rate-limit, quota - null / pass-through in v1) then calls `project` on
the best view. Not a Manifold itself: it can reject / throttle, it does not project. Served profiles
always materialize a Coverage; a non-Coverage result is a bug (non-taxonomy error). Exactly one
Gateway exists per woven profile, which is why releasing it releases the profile.
See docs/architecture.md ("Gateway").

Sits above the surfaces rather than inside `api/`, and carries the `Closeable` facet. Nothing that
realizes `Closeable` imports it: the Protocol is structural, so `nodes/` never depends on this module
and composition lifetime stays outside the algebra. See docs/module-layout.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from .manifold.core import Coverage, Manifold, Selection


@runtime_checkable
class Closeable(Protocol):
    """Facet: holds a resource outliving a single call, so a composition must release it.

    Whatever holds nothing implements nothing. See docs/glossary.md.
    """

    async def aclose(self) -> None: ...


class Gateway:
    def __init__(self, best_view: Manifold, *sites: Iterable[object]) -> None:
        """Each `sites` argument is one construction site's output, in construction order.

        A caller names *where* things were built and nothing else; which of them are `Closeable` is
        this boundary's question, so a site may contain anything and mostly does.
        """
        self.best_view = best_view
        self._closeables = tuple(
            built for site in sites for built in site if isinstance(built, Closeable)
        )

    async def resolve(self, selection: Selection) -> Coverage:
        result = await self.best_view.project(selection)
        if not isinstance(result, Coverage):
            # TODO(#39): give engine invariant breaks their own public failure category; neither the
            # request nor a producer is at fault.
            raise TypeError(f"best view must project to Coverage, got {type(result).__name__}")
        return result

    async def aclose(self) -> None:
        """Release the whole composition, in reverse of the order it was given.

        Reverse, because a thing built later may be built on an earlier one. Total: every
        `Closeable` is attempted even after one fails, and the failures surface together as an
        `ExceptionGroup`. Idempotent by emptying the list before the first `await` - a second call,
        after a failure or from another task, releases nothing and needs no lock. Cancellation
        therefore strands the rest, deliberately: `CancelledError` is a `BaseException`, so it
        propagates rather than joining the group; catching it to keep going would swallow the
        cancellation.

        TODO(#14): report each failure through the logging boundary. Until then the raised group is
        the only report, and a teardown message must never carry a connection string.
        """
        closeables = self._closeables
        self._closeables = ()
        failures: list[Exception] = []
        for closeable in reversed(closeables):
            try:
                await closeable.aclose()
            except Exception as failure:
                failures.append(failure)
        if failures:
            raise ExceptionGroup("composition teardown failed", failures)
