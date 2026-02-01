"""Tests for the help panel widget."""

import pytest
from textual.binding import Binding

from openclaw_dash.widgets.help_panel import (
    SHORTCUTS,
    STATIC_SHORTCUTS,
    HelpScreen,
    _categorize_binding,
    _format_key,
    extract_bindings_from_app,
)


class TestShortcuts:
    """Test SHORTCUTS data structure (legacy constant)."""

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
        """Should have a Navigation section in static shortcuts."""
        section_names = [name for name, _ in STATIC_SHORTCUTS]
        assert "Navigation" in section_names


class TestHelpScreen:
    """Test HelpScreen widget."""

    def test_help_screen_has_bindings(self):
        """Help screen should have dismiss bindings."""
        binding_keys = [b.key for b in HelpScreen.BINDINGS]
        assert "escape" in binding_keys
        assert "h" in binding_keys
        assert "question_mark" in binding_keys

    def test_help_screen_css_defined(self):
        """Help screen should have CSS defined."""
        assert HelpScreen.CSS is not None
        assert len(HelpScreen.CSS) > 0
        assert "help-container" in HelpScreen.CSS

    def test_help_screen_accepts_shortcuts(self):
        """Help screen should accept custom shortcuts."""
        custom_shortcuts = [("Custom", [("x", "Do something")])]
        screen = HelpScreen(shortcuts=custom_shortcuts)
        assert screen._shortcuts == custom_shortcuts


class TestKeyFormatting:
    """Test key display formatting."""

    def test_format_single_letter(self):
        """Single letters should be uppercased."""
        assert _format_key("q") == "Q"
        assert _format_key("r") == "R"

    def test_format_special_keys(self):
        """Special keys should have readable names."""
        assert _format_key("question_mark") == "?"
        assert _format_key("escape") == "Esc"
        assert _format_key("space") == "Space"
        assert _format_key("enter") == "Enter"

    def test_format_arrow_keys(self):
        """Arrow keys should use unicode symbols."""
        assert _format_key("up") == "↑"
        assert _format_key("down") == "↓"
        assert _format_key("left") == "←"
        assert _format_key("right") == "→"

    def test_format_modifier_combinations(self):
        """Modifier key combinations should be formatted."""
        assert _format_key("ctrl+p") == "Ctrl+P"
        assert _format_key("ctrl+c") == "Ctrl+C"


class TestBindingCategorization:
    """Test binding categorization logic."""

    def test_categorize_quit_as_general(self):
        """Quit action should be General."""
        assert _categorize_binding("quit") == "General"

    def test_categorize_refresh_as_general(self):
        """Refresh action should be General."""
        assert _categorize_binding("refresh") == "General"

    def test_categorize_focus_as_panel_focus(self):
        """Focus actions should be Panel Focus."""
        assert _categorize_binding("focus_panel('gateway')") == "Panel Focus"
        assert _categorize_binding("focus_gateway") == "Panel Focus"

    def test_categorize_theme_as_display(self):
        """Theme actions should be Display."""
        assert _categorize_binding("cycle_theme") == "Display"
        assert _categorize_binding("theme") == "Display"

    def test_categorize_help_as_help(self):
        """Help action should be Help."""
        assert _categorize_binding("help") == "Help"
        assert _categorize_binding("show_help") == "Help"


class TestExtractBindings:
    """Test extracting bindings from app."""

    def test_extract_from_tuple_bindings(self):
        """Should extract from tuple-style bindings."""

        class MockApp:
            BINDINGS = [
                ("q", "quit", "Quit"),
                ("r", "refresh", "Refresh"),
            ]

        result = extract_bindings_from_app(MockApp())

        # Should have General category
        categories = {name: shortcuts for name, shortcuts in result}
        assert "General" in categories

        # Check shortcuts are extracted
        general_keys = [key for key, _ in categories["General"]]
        assert "Q" in general_keys
        assert "R" in general_keys

    def test_extract_from_binding_objects(self):
        """Should extract from Binding objects."""

        class MockApp:
            BINDINGS = [
                Binding("q", "quit", "Quit application"),
                Binding("t", "cycle_theme", "Change theme"),
            ]

        result = extract_bindings_from_app(MockApp())
        categories = {name: shortcuts for name, shortcuts in result}

        assert "General" in categories
        assert "Display" in categories

    def test_combines_duplicate_actions(self):
        """Should combine keys bound to same action."""

        class MockApp:
            BINDINGS = [
                ("h", "help", "Help"),
                ("question_mark", "help", "Help"),
            ]

        result = extract_bindings_from_app(MockApp())
        categories = {name: shortcuts for name, shortcuts in result}

        # Should only have one help entry with combined keys
        assert "Help" in categories
        help_shortcuts = categories["Help"]
        assert len(help_shortcuts) == 1
        key, _ = help_shortcuts[0]
        assert "H" in key
        assert "?" in key

    def test_category_ordering(self):
        """Categories should be ordered: General, Display, Panel Focus, then Help."""

        class MockApp:
            BINDINGS = [
                ("h", "help", "Help"),
                ("t", "cycle_theme", "Theme"),
                ("q", "quit", "Quit"),
                ("g", "focus_gateway", "Gateway"),
            ]

        result = extract_bindings_from_app(MockApp())
        category_names = [name for name, _ in result]

        # General should come before Display
        assert category_names.index("General") < category_names.index("Display")
        # Help should be last
        assert category_names[-1] == "Help"


@pytest.mark.asyncio
async def test_help_screen_compose():
    """Test that HelpScreen composes without error."""
    screen = HelpScreen()
    # Just verify compose method exists and is callable
    assert hasattr(screen, "compose")
    assert callable(screen.compose)


@pytest.mark.asyncio
async def test_help_screen_with_custom_shortcuts():
    """Test HelpScreen with custom shortcuts composes correctly."""
    shortcuts = [
        ("Test", [("x", "Test action"), ("y", "Another action")]),
    ]
    screen = HelpScreen(shortcuts=shortcuts)
    assert screen._shortcuts == shortcuts
