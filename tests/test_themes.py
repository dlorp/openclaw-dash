"""Tests for the themes module."""

from openclaw_dash.themes import (
    DARK_ORANGE,
    DARK_THEME,
    GRANITE_GRAY,
    HACKER_THEME,
    LIGHT_THEME,
    MEDIUM_TURQUOISE,
    ROYAL_BLUE_LIGHT,
    THEME_NAMES,
    THEMES,
    TITANIUM_YELLOW,
    BrandColors,
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


class TestBrandColors:
    """Tests for dlorp brand color definitions."""

    def test_granite_gray_defined(self) -> None:
        """Granite Gray should be defined for borders."""
        assert GRANITE_GRAY == "#636764"
        assert BrandColors.GRANITE_GRAY == "#636764"

    def test_dark_orange_defined(self) -> None:
        """Dark Orange should be defined for warnings."""
        assert DARK_ORANGE == "#FB8B24"
        assert BrandColors.DARK_ORANGE == "#FB8B24"

    def test_titanium_yellow_defined(self) -> None:
        """Titanium Yellow should be defined for highlights."""
        assert TITANIUM_YELLOW == "#F4E409"
        assert BrandColors.TITANIUM_YELLOW == "#F4E409"

    def test_medium_turquoise_defined(self) -> None:
        """Medium Turquoise should be defined for success."""
        assert MEDIUM_TURQUOISE == "#50D8D7"
        assert BrandColors.MEDIUM_TURQUOISE == "#50D8D7"

    def test_royal_blue_defined(self) -> None:
        """Royal Blue Light should be defined for primary."""
        assert ROYAL_BLUE_LIGHT == "#3B60E4"
        assert BrandColors.ROYAL_BLUE_LIGHT == "#3B60E4"

    def test_all_brand_colors_are_valid_hex(self) -> None:
        """All brand colors should be valid hex color codes."""
        colors = [
            GRANITE_GRAY,
            DARK_ORANGE,
            TITANIUM_YELLOW,
            MEDIUM_TURQUOISE,
            ROYAL_BLUE_LIGHT,
        ]
        for color in colors:
            assert color.startswith("#")
            assert len(color) == 7
            # Check that all chars after # are valid hex
            int(color[1:], 16)  # Will raise if invalid

    def test_dark_theme_uses_brand_primary(self) -> None:
        """Dark theme should use brand turquoise as primary."""
        assert DARK_THEME.primary == MEDIUM_TURQUOISE

    def test_dark_theme_uses_brand_secondary(self) -> None:
        """Dark theme should use brand blue as secondary."""
        assert DARK_THEME.secondary == ROYAL_BLUE_LIGHT

    def test_dark_theme_uses_brand_accent(self) -> None:
        """Dark theme should use brand orange as accent."""
        assert DARK_THEME.accent == DARK_ORANGE
