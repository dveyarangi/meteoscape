"""The shipped provider set — availability is a system prop.

The handle IS the impl id (a plain string): profile authors import one module and never
retype a name, and defs keep plain-string fields with no coercion. Anyone needing the
manifest object reads `CATALOG[handle]`. `catalog/` stays faces-only; this module imports
the concrete plugins. docs/concerns.md#26-provider--calculator-plugin-scaffolding
"""

from ..catalog.providers import ProviderCatalog
from .open_meteo import IMPL_ID as OPEN_METEO
from .open_meteo import MANIFEST as _OPEN_METEO_MANIFEST
from .twc import IMPL_ID as TWC
from .twc import MANIFEST as _TWC_MANIFEST

CATALOG: ProviderCatalog = {TWC: _TWC_MANIFEST, OPEN_METEO: _OPEN_METEO_MANIFEST}
