"""Options for the opt-in live parity checks (`uv run pytest tests/parity`)."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--twc-api-key",
        default=None,
        help="TWC API key for the live parity check; overrides METEOSCAPE_TWC_API_KEY.",
    )
