"""Injected catalogues — process-wide, settings-materialized plugin faces above `manifold/`.

Each catalogue is a static map the composition root hands to a binder: `ParameterTable`
(`ParameterId → ParameterDef`), `ProviderCatalog` (`impl_id → ProviderManifest`), `CalculatorCatalog`
(`fn_id → CalculatorManifest`). They carry vocabulary + cohesive plugin faces (declarations *and*
their `build`), never data flow. Unlike the `parameters` vocabulary leaf, these sit above `manifold/`
because their faces name algebra types (`EnumerableDomain`) and `Provider`. See ADR-0005.
"""
