"""The parameter catalog: the vocabulary and the injected `ParameterTable` lookup - *what a parameter
is*, not the algebra.

A leaf package that depends on nothing inward, so `manifold/` imports it, never the reverse. (The
runtime `ParameterData` slice is *not* here - it carries no catalog facts, so it lives with the
Coverage value model in `manifold/data.py`.)
"""
