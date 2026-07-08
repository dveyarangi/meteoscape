"""Observability init seam.

A single, config-driven entry point that the composition root (`server.py`) calls once at startup.
Kept out of the Manifold contract: it is operational infrastructure, not part of the algebra.

DSN is optional. Absent DSN is a no-op (the server runs without error reporting), mirroring
the optional-secret graceful-degrade rule the rest of v1 follows for provider keys.
"""

from __future__ import annotations

import os

_SENTRY_DSN_ENV = "SENTRY_DSN"
_ENVIRONMENT_ENV = "METEOSCAPE_ENV"


def init_observability(dsn: str | None = None, *, environment: str | None = None) -> bool:
    """Initialize error reporting if a DSN is configured.

    `dsn` is taken from the argument first, then the `SENTRY_DSN` env var. When neither is
    present this is a no-op and returns `False` so a missing/optional secret degrades
    gracefully instead of failing startup.

    Returns `True` iff Sentry was initialized.
    """
    resolved_dsn = dsn or os.environ.get(_SENTRY_DSN_ENV)
    if not resolved_dsn:
        return False

    import sentry_sdk

    sentry_sdk.init(
        dsn=resolved_dsn,
        environment=environment or os.environ.get(_ENVIRONMENT_ENV),
    )
    return True
