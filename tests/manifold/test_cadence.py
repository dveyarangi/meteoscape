"""CadenceDef — run anchor, expiration, and rolling valid_time window."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from meteoscape.manifold.cadence import CadenceDef
from meteoscape.manifold.domain import Interval


def test_cadence_anchor_expiration_and_valid_time() -> None:
    cadence = CadenceDef(
        cadence=timedelta(hours=1),
        publication_latency=timedelta(minutes=20),
        max_lead=timedelta(hours=6),
    )
    # Publication of the 12:00 run is 12:20. Just before → still on 11:00 run.
    just_before = datetime(2026, 7, 11, 12, 19, tzinfo=UTC)
    assert cadence.anchor(just_before) == datetime(2026, 7, 11, 11, 0, tzinfo=UTC)

    at_publication = datetime(2026, 7, 11, 12, 20, tzinfo=UTC)
    assert cadence.anchor(at_publication) == datetime(2026, 7, 11, 12, 0, tzinfo=UTC)

    a = cadence.anchor(at_publication)
    assert cadence.expiration(at_publication) == a + timedelta(hours=1) + timedelta(minutes=20)
    assert cadence.valid_time(at_publication) == Interval(a, a + timedelta(hours=6))
