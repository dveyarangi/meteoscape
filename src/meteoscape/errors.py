"""Error taxonomy.

The three first-class failure categories the engine distinguishes, mapped to protocol errors at
the surface adapter. Distinct from a successful *nodata* gap (`present[i] is False`), which is data,
not an error. See architecture.md - "Failure, nodata, and availability".
"""

from __future__ import annotations


class MeteoscapeError(Exception):
    """Root of the error taxonomy."""


class BadRequest(MeteoscapeError):
    """The request itself is malformed or invalid (e.g. an out-of-range lat/lon).

    Caller-fixable: the input must change.
    """


class CapabilityMismatch(MeteoscapeError):
    """No producer declares the requested parameter / extent.

    The request is well-formed but unservable by the wired producers; the parameter is omitted
    from the record (a whole-request error only when nothing is produced).
    """


class RuntimeFailure(MeteoscapeError):
    """A producer could not produce: 5xx, timeout, malformed upstream response.

    An exception that makes the Arbiter fall through to the next candidate.
    """


class CompositionError(Exception):
    """Build-time failure - a misconfigured profile the server refuses to start with: unknown catalogue
    entry, dangling secret, duplicate key, missing StoreSpec, or a reach that cannot compose (sheared
    footprints, non-separable geometry).

    A Tier-0 leaf so every layer that composes can raise it - the reconciler naming a parameter, a
    derived capability naming its calculator - rather than one translating another's error. Outside the
    request-surface taxonomy (`MeteoscapeError`): it never reaches a client, it stops the boot.
    """
