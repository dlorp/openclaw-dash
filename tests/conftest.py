"""Pytest configuration for openclaw-dash tests."""

import pytest

from openclaw_dash import demo


@pytest.fixture(autouse=True)
def enable_demo_mode_for_tests():
    """Enable demo mode for all tests to avoid real network/subprocess calls."""
    demo.enable_demo_mode()
    yield
    demo.disable_demo_mode()
