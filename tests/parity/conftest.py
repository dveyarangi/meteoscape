"""Options for the opt-in live parity checks (`uv run pytest tests/parity`)."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--twc-api-key",
        default=None,
        help="TWC API key for the live parity check; overrides METEOSCAPE_TWC_API_KEY.",
    )
    parser.addoption(
        "--provider-order",
        default="twc,open-meteo",
        help="Comma-separated impl ids for the composite serving-order check (priority = index).",
    )
