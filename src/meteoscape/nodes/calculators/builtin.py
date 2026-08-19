"""The shipped calculator set — availability is a system prop.

The handle IS the fn id (a plain string): profile authors import one module and never
retype a name, and defs keep plain-string fields with no coercion. Anyone needing the
manifest object reads `CATALOG[handle]`. `catalog/` stays faces-only; this module imports
the concrete plugins. docs/concerns.md#26-provider--calculator-plugin-scaffolding
"""

from ..catalog.calculators import CalculatorCatalog
from .wind import MANIFEST as _WIND_UV_MANIFEST

WIND_UV = _WIND_UV_MANIFEST.fn_id

CATALOG: CalculatorCatalog = {WIND_UV: _WIND_UV_MANIFEST}
