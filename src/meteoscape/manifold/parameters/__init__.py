"""Parameter vocabulary and the injected `ParameterTable` seam.

Consumers (Normalizer, Capability, the edge) reach parameter facts by injection of a
`ParameterTable`, never via hardcoded enums.
"""
