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

    Presence is read through behaviour (`is_present` / `of` / `take`); `None` is an elided all-present
    representation, not a contract consumers should branch on. Planned numpy/xarray backing stays
    behind this interface.
    """

    values: Sequence[float]
    present: Sequence[bool] | None

    def __post_init__(self) -> None:
        if self.present is not None and len(self.present) != len(self.values):
            raise ValueError(
                f"present length {len(self.present)} != values length {len(self.values)}"
            )

    @classmethod
    def of(cls, values: Sequence[float], present: Sequence[bool]) -> ParameterData:
        """Construct, eliding an all-present mask. Elides only a *validated* mask."""
        validated = cls(values=values, present=present)
        return cls(values=values, present=None) if all(present) else validated

    def is_present(self, i: int) -> bool:
        return self.present is None or self.present[i]

    def take(self, indices: Sequence[int]) -> ParameterData:
        """Gather the slice at `indices` — values and presence stay in step by construction."""
        values = [self.values[i] for i in indices]
        if self.present is None:
            return ParameterData(values=values, present=None)
        return ParameterData.of(values, [self.present[i] for i in indices])


def and_present(
    left: Sequence[bool] | None, right: Sequence[bool] | None, *, n: int
) -> Sequence[bool] | None:
    """Elementwise AND of two present masks; `None` means all-present."""
    if left is None and right is None:
        return None
    a = left if left is not None else (True,) * n
    b = right if right is not None else (True,) * n
    return [x and y for x, y in zip(a, b, strict=True)]
