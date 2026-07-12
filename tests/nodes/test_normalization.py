"""Normalizer protocol — vendor shape → canonical semantics in native geometry."""

from __future__ import annotations

from datetime import UTC, datetime

from fakes import point_timeline_domain
from meteoscape.identity import SourceKey
from meteoscape.manifold.capability import EnumerableCapability
from meteoscape.manifold.core import Coverage
from meteoscape.manifold.coverage import CoverageRecord
from meteoscape.manifold.data import ParameterData
from meteoscape.manifold.provenance import AtomicOrigin, Provenance, Uniform
from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.nodes.providers.normalization import Normalizer
from meteoscape.parameters import AIR_TEMPERATURE


def test_normalizer_contract_takes_raw_and_provenance() -> None:
    """Locks `normalize(raw, provenance) -> Coverage` (no selection — homogenization is Reservoir)."""
    domain = point_timeline_domain(hours=1)
    table = StaticParameterTable.core()
    provenance = Provenance(
        origin=AtomicOrigin(SourceKey("open-meteo", "best_match"), datetime(2026, 7, 11, tzinfo=UTC)),
        fetched_at=datetime(2026, 7, 11, 12, tzinfo=UTC),
        expiration=datetime(2026, 7, 11, 13, tzinfo=UTC),
    )
    expected = CoverageRecord(
        capability=EnumerableCapability(
            domain=domain,
            parameters={AIR_TEMPERATURE: table.get(AIR_TEMPERATURE)},
        ),
        ranges={AIR_TEMPERATURE: ParameterData(values=[18.5], present=None)},
        provenance=Uniform(provenance),
    )

    class _Stub:
        def normalize(self, raw: object, provenance: Provenance) -> Coverage:
            assert raw == {"temperature_2m": [18.5]}
            assert provenance.origin.source.provider == "open-meteo"
            return expected

    normalizer: Normalizer = _Stub()
    assert normalizer.normalize({"temperature_2m": [18.5]}, provenance) is expected
