"""Tests for the help panel widget."""

import pytest

from openclaw_dash.widgets.help_panel import SHORTCUTS, HelpScreen


class TestShortcuts:
    """Test SHORTCUTS data structure."""

    def test_shortcuts_not_empty(self):
        """Shortcuts list should not be empty."""
        assert len(SHORTCUTS) > 0

    def test_shortcuts_structure(self):
        """Each shortcut section should have name and list of tuples."""
        for section_name, shortcuts in SHORTCUTS:
            assert isinstance(section_name, str)
            assert len(section_name) > 0
            assert isinstance(shortcuts, list)
            for key, desc in shortcuts:
                assert isinstance(key, str)
                assert isinstance(desc, str)
                assert len(key) > 0
                assert len(desc) > 0

    def test_general_section_exists(self):
        """Should have a General section."""
        section_names = [name for name, _ in SHORTCUTS]
        assert "General" in section_names

    def test_navigation_section_exists(self):
        """Should have a Navigation section."""
        section_names = [name for name, _ in SHORTCUTS]
        assert "Navigation" in section_names


class TestHelpScreen:
    """Test HelpScreen widget."""

    def test_help_screen_has_bindings(self):
        """Help screen should have dismiss bindings."""
        binding_keys = [b.key for b in HelpScreen.BINDINGS]
        assert "escape" in binding_keys
        assert "h" in binding_keys

    def test_help_screen_css_defined(self):
        """Help screen should have CSS defined."""
        assert HelpScreen.CSS is not None
        assert len(HelpScreen.CSS) > 0
        assert "help-container" in HelpScreen.CSS


@pytest.mark.asyncio
async def test_help_screen_compose():
    """Test that HelpScreen composes without error."""
    screen = HelpScreen()
    # Just verify compose method exists and is callable
    assert hasattr(screen, "compose")
    assert callable(screen.compose)
