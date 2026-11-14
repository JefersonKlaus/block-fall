"""Fixtures shared by the whole test suite.

The app lives in src/ (the usual Flet layout); pytest puts it on sys.path
(see `pythonpath` in pyproject.toml), so tests import it as `game`, `ui`, ...
"""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def sleep(monkeypatch):
    """Replace animation pauses with instant, recorded ones."""
    mock = AsyncMock()
    monkeypatch.setattr("ui.animation.asyncio.sleep", mock)
    return mock
