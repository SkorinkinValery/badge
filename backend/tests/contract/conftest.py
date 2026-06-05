"""Contract test fixtures — parametrised by port implementation.

Each port fixture returns a list of (label, impl) pairs.
Stub implementations are registered here; real adapters extend this list in M3/M4/M8.
"""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "contract: marks contract tests for port implementations",
    )
