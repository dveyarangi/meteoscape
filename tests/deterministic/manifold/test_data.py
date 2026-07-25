"""ParameterData — presence behaviour and construction invariants."""

from __future__ import annotations

import pytest

from meteoscape.manifold.data import ParameterData


def test_mismatched_present_length_rejected() -> None:
    with pytest.raises(ValueError, match="present length"):
        ParameterData(values=[1.0, 2.0], present=[True])


def test_of_rejects_short_all_true_mask() -> None:
    """D1: elision must not swallow a length violation before validation sees it."""
    with pytest.raises(ValueError, match="present length"):
        ParameterData.of(values=[1.0, 2.0], present=[True])


def test_of_elides_all_present_mask() -> None:
    data = ParameterData.of(values=[1.0, 2.0], present=[True, True])
    assert data.present is None
    assert list(data.values) == [1.0, 2.0]


def test_of_preserves_mixed_mask() -> None:
    data = ParameterData.of(values=[1.0, 2.0, 3.0], present=[True, False, True])
    assert data.present is not None
    assert list(data.present) == [True, False, True]


def test_is_present_agrees_for_both_representations() -> None:
    elided = ParameterData(values=[1.0, 2.0], present=None)
    assert elided.is_present(0) is True
    assert elided.is_present(1) is True

    mixed = ParameterData(values=[1.0, 2.0], present=[True, False])
    assert mixed.is_present(0) is True
    assert mixed.is_present(1) is False


def test_take_keeps_values_and_presence_in_step() -> None:
    data = ParameterData.of([10.0, 11.0, 12.0], [True, False, True])
    cropped = data.take([0, 1])
    assert list(cropped.values) == [10.0, 11.0]
    assert cropped.is_present(0) is True
    assert cropped.is_present(1) is False


def test_take_re_elides_when_crop_removes_every_absent() -> None:
    data = ParameterData.of([10.0, 11.0, 12.0], [True, False, True])
    cropped = data.take([0, 2])
    assert list(cropped.values) == [10.0, 12.0]
    assert cropped.present is None
    assert cropped.is_present(0) is True
    assert cropped.is_present(1) is True
