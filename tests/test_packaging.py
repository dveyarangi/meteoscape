"""Packaging smoke test.

Verifies the distribution imports in a fresh environment. This is a CI liveness check, not a
behavioural test; issue 001+ adds the MCP-startup smoke test and behaviour-bearing suites.
"""

import meteoscape


def test_package_imports() -> None:
    assert callable(meteoscape.main)
