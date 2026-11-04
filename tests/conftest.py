"""Shared fixtures."""
from datetime import date

import pytest


@pytest.fixture
def today() -> date:
    return date(2026, 1, 10)
