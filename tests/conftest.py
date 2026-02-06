"""Pytest configuration for openclaw-dash tests."""

import pytest

from openclaw_dash import demo


@pytest.fixture(autouse=True)
def disable_demo_mode_for_tests():
    """Ensure demo mode is disabled for all tests.

    Tests should use mocks/patches to control behavior, not demo mode.
    Tests that explicitly need demo mode can use the demo_mode fixture.
    """
    demo.disable_demo_mode()
    yield
    demo.disable_demo_mode()


@pytest.fixture
def demo_mode():
    """Fixture to explicitly enable demo mode for specific tests."""
    demo.enable_demo_mode()
    yield
    demo.disable_demo_mode()
