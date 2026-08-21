"""Surface adapters between protocols and the canonical model.

Translate a surface protocol to/from the canonical model, and drive the composition they are
handed. Caller policy is the `Gateway`'s, one level up.

What a surface reaches for is bounded by what it does: the algebra it serializes, the `Gateway` it
was given, and `nodes/catalog`'s `ParameterTable` to name parameters with. It never touches the
graph-building machinery - no binder, no `Weaver`, no node - because a surface receives a
composition and never builds one.
"""
