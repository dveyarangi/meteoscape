"""`ParameterData` - one parameter's materialized value slice in a Coverage.

Pure numbers - `values` positional to the Coverage's Domain plus a `present` mask - and nothing else:
descriptors ride the Coverage's `capability` (its `ParameterDef`s) and provenance is the Coverage
plane, so no id-entailed fact is denormalized onto the slice. See ADR-0002 / ADR-0003.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ParameterData:
    """`present is None` => all cells present; `present[i] is False` => nodata (a successful gap).

    `values` is typed abstractly here; its concrete array backing is decided when behaviour lands
    (numpy/xarray stay behind this interface).
    """

    values: Sequence[float]
    present: Sequence[bool] | None


def and_present(
    left: Sequence[bool] | None, right: Sequence[bool] | None, *, n: int
) -> Sequence[bool] | None:
    """Elementwise AND of two present masks; `None` means all-present."""
    if left is None and right is None:
        return None
    a = left if left is not None else (True,) * n
    b = right if right is not None else (True,) * n
    return [x and y for x, y in zip(a, b, strict=True)]
