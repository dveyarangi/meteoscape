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
