"""Atomic origin identity, run-free origins, and the never-expires stamp."""

from datetime import UTC, datetime

from meteoscape.identity import SourceKey
from meteoscape.manifold.provenance import AtomicOrigin

_KEY = SourceKey("collector-obs", "stations")
_RUN = datetime(2026, 7, 11, 12, tzinfo=UTC)


def test_atomic_origin_identity_defaults_absent() -> None:
    origin = AtomicOrigin(_KEY, _RUN)
    assert origin.authority is None
    assert origin.process is None
    assert origin.unit is None


def test_atomic_origin_carries_identity_when_given() -> None:
    origin = AtomicOrigin(_KEY, _RUN, authority="agrometeo", process="instant", unit="Russel")
    assert origin.authority == "agrometeo"
    assert origin.process == "instant"
    assert origin.unit == "Russel"


def test_run_free_origin_has_no_issue_time() -> None:
    origin = AtomicOrigin(_KEY, None)
    assert origin.issue_time is None
