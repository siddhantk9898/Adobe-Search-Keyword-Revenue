"""Shared test fixtures."""

import pytest
from src.config import Config


@pytest.fixture(autouse=True)
def reset_config():
    """Reset the Config singleton before each test so tests are isolated."""
    Config.reset()
    yield
    Config.reset()
