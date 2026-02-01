"""Tests for the themes module."""

from openclaw_dash.themes import (
    DARK_THEME,
    HACKER_THEME,
    LIGHT_THEME,
    THEME_NAMES,
    THEMES,
    get_theme,
    next_theme,
)


class TestThemeDefinitions:
    """Tests for theme definitions."""

    def test_three_themes_defined(self) -> None:
        """Should have exactly 3 themes."""
        assert len(THEMES) == 3

    def test_theme_names_match(self) -> None:
        """Theme names list should match themes."""
        assert THEME_NAMES == ["dark", "light", "hacker"]

    def test_dark_theme_is_dark(self) -> None:
        """Dark theme should have dark=True."""
        assert DARK_THEME.dark is True

    def test_light_theme_is_light(self) -> None:
        """Light theme should have dark=False."""
        assert LIGHT_THEME.dark is False

    def test_hacker_theme_is_dark(self) -> None:
        """Hacker theme should have dark=True."""
        assert HACKER_THEME.dark is True

    def test_all_themes_have_names(self) -> None:
        """All themes should have valid names."""
        for theme in THEMES:
            assert theme.name
            assert isinstance(theme.name, str)


class TestGetTheme:
    """Tests for get_theme function."""

    def test_get_dark_theme(self) -> None:
        """Should return dark theme by name."""
        theme = get_theme("dark")
        assert theme.name == "dark"

    def test_get_light_theme(self) -> None:
        """Should return light theme by name."""
        theme = get_theme("light")
        assert theme.name == "light"

    def test_get_hacker_theme(self) -> None:
        """Should return hacker theme by name."""
        theme = get_theme("hacker")
        assert theme.name == "hacker"

    def test_unknown_theme_returns_dark(self) -> None:
        """Should return dark theme for unknown names."""
        theme = get_theme("nonexistent")
        assert theme.name == "dark"


class TestNextTheme:
    """Tests for next_theme function."""

    def test_dark_to_light(self) -> None:
        """Dark should cycle to light."""
        assert next_theme("dark") == "light"

    def test_light_to_hacker(self) -> None:
        """Light should cycle to hacker."""
        assert next_theme("light") == "hacker"

    def test_hacker_to_dark(self) -> None:
        """Hacker should cycle back to dark."""
        assert next_theme("hacker") == "dark"

    def test_unknown_returns_first(self) -> None:
        """Unknown theme should return first theme."""
        assert next_theme("nonexistent") == "dark"

    def test_full_cycle(self) -> None:
        """Should complete full cycle back to start."""
        theme = "dark"
        for _ in range(3):
            theme = next_theme(theme)
        assert theme == "dark"
