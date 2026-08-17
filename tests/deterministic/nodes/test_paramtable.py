"""StaticParameterTable.core() — v1 ParameterDef catalogue."""

from meteoscape.nodes.catalog.paramtable import StaticParameterTable
from meteoscape.parameters import AIR_TEMPERATURE, RELATIVE_HUMIDITY


def test_core_table_declares_screen_allowance_on_temperature_and_humidity() -> None:
    """The v1 bands live on the Parameter, matching parameters.md, not on any producer."""
    table = StaticParameterTable.core()
    banded = {
        pid: table.get(pid).z_allowance for pid in table if table.get(pid).z_allowance is not None
    }
    assert banded == {
        AIR_TEMPERATURE: (1.25, 2.0),
        RELATIVE_HUMIDITY: (1.25, 2.0),
    }
